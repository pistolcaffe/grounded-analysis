import re
from dataclasses import dataclass, field
from typing import Optional

KNOWN_COLUMNS = {"push_sent", "active_users", "revenue", "support_tickets"}
_COL_PAT = "|".join(KNOWN_COLUMNS)

_LABEL_RE = re.compile(r"^\s*\[(VERIFIED|INFERENCE|ASSUMPTION)\]\s*(.*)", re.IGNORECASE)
_PAREN_RE = re.compile(r"\((.+)\)\s*\.?\s*$", re.DOTALL)
_CALC_SPLIT_RE = re.compile(r";\s*calculation\s*:", re.IGNORECASE)
_SOURCE_PREFIX_RE = re.compile(r"^source\s*:\s*", re.IGNORECASE)

# Source ref patterns
_PAT_WEEK_COL_VAL = re.compile(
    r"\b(W\d+)\s+(" + _COL_PAT + r")\s+(\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)
_PAT_WEEK_EQ_VAL = re.compile(r"\b(W\d+)\s*=\s*(\d[\d,]*(?:\.\d+)?)")
_PAT_COL_ARRAY = re.compile(
    r"(" + _COL_PAT + r")\s+array\s+\[([^\]]+)\]",
    re.IGNORECASE,
)
_WEEKS_ORDERED = ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"]

# Bullet-style explicit formula/source line: "- Source: ..." / "- Formula: ..."
_BULLET_FORMULA_RE = re.compile(
    r"^[-*]\s*(?:source|formula)[:\s]+(.*)",
    re.IGNORECASE | re.MULTILINE,
)
# Fallback: any bullet line containing "= <number>" (handles "- Description: expr = result")
_BULLET_EQ_RE = re.compile(
    r"^[-*]\s+.+=\s*\*{0,2}[+\-]?[\d,]+(?:\.\d+)?%?\*{0,2}",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class SourceRef:
    week: Optional[str]
    column: Optional[str]
    value: Optional[float]

    def __str__(self) -> str:
        parts = [p for p in [self.week, self.column,
                              str(self.value) if self.value is not None else None] if p]
        return " ".join(parts)


@dataclass
class Claim:
    label: str                              # VERIFIED | INFERENCE | ASSUMPTION
    text: str                               # full text after the label prefix
    source_refs: list[SourceRef] = field(default_factory=list)
    formula_lhs: Optional[str] = None      # arithmetic expression (left of =)
    formula_rhs: Optional[str] = None      # claimed result (right of last =)
    parse_ok: bool = True                   # False when formula extraction failed


# ---------------------------------------------------------------------------
# Formula normalization
# ---------------------------------------------------------------------------

def _normalize_formula(s: str) -> str:
    """Whole-formula normalization applied before splitting on '='."""
    s = s.replace("−", "-")                                 # Unicode minus → ASCII
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)               # **bold** → inner text
    s = re.sub(r"[×xX]\s*$", "", s)                        # trailing × (ratio)
    s = re.sub(r"\s+[a-zA-Z][a-zA-Z\s]*$", "", s.rstrip()) # trailing words like "increase"
    return s.strip()


def _normalize_segment(s: str) -> str:
    """Per-segment normalization applied after splitting on '='."""
    s = s.strip()
    s = re.sub(r"\*+", "", s)                               # strip all stray * (bold artifacts)
    s = s.lstrip("+")                                       # leading + (e.g. +8.3%)
    s = re.sub(r"[×xX]\s*$", "", s)                        # trailing ×
    s = re.sub(r"\s+[a-zA-Z][a-zA-Z\s]*$", "", s)          # trailing words
    return s.rstrip(". ").strip()


def _trim_to_arithmetic(s: str) -> Optional[str]:
    """Extract arithmetic expression from a segment that may have a descriptive prefix.

    Tries common separator patterns (→ arrow, ': ') to find where the
    arithmetic expression starts.
    """
    # After → arrow  (e.g. "W1 vs W3 → (8000 - 5000) / 5000")
    for arrow in ["→", "->"]:
        idx = s.rfind(arrow)
        if idx != -1:
            cand = s[idx + len(arrow):].strip()
            if cand and (cand[0].isdigit() or cand[0] in "(-"):
                return cand

    # After last ': '  (e.g. "Revenue growth: (5200-4800)/4800")
    idx = s.rfind(": ")
    if idx != -1:
        cand = s[idx + 2:].strip()
        if cand and (cand[0].isdigit() or cand[0] in "(-"):
            return cand

    # After last '. '  (e.g. "...W6 = $5200. Change: (expr)/base")
    idx = s.rfind(". ")
    if idx != -1:
        cand = s[idx + 2:].strip()
        if cand and (cand[0].isdigit() or cand[0] in "(-"):
            return cand

    # Whole segment is already arithmetic (starts with digit or open paren)
    if s and (s[0].isdigit() or s[0] in "(-"):
        return s

    return None


def _parse_calculation_multi(calc_text: str) -> tuple[Optional[str], Optional[str]]:
    """Parse a formula string that may contain multiple '=' signs.

    Handles chains like "A = B = C" (intermediate steps):
    - Scans segments left-to-right for the first evaluatable arithmetic expression
    - Uses the last segment as the claimed result (RHS)

    Also handles:
    - Unicode minus (−)
    - Bold markdown (**value**)
    - Trailing ×, trailing words like "increase"
    - Descriptive prefixes before formulas (trimmed via _trim_to_arithmetic)
    - Leading '+' in percent values
    """
    text = _normalize_formula(calc_text)
    segments = [_normalize_segment(s) for s in text.split("=")]
    segments = [s for s in segments if s]
    if len(segments) < 2:
        return None, None

    rhs = segments[-1]

    # Scan from left to find the first segment with an extractable arithmetic expression
    for seg in segments[:-1]:
        candidate = _trim_to_arithmetic(seg)
        if candidate:
            return candidate, rhs

    return None, rhs


# ---------------------------------------------------------------------------
# Source ref parsing
# ---------------------------------------------------------------------------

def _parse_source_refs(source_text: str) -> list[SourceRef]:
    refs: list[SourceRef] = []
    seen: set[tuple] = set()

    for m in _PAT_WEEK_COL_VAL.finditer(source_text):
        week, col = m.group(1).upper(), m.group(2).lower()
        val = float(m.group(3).replace(",", ""))
        if (week, col) not in seen:
            refs.append(SourceRef(week=week, column=col, value=val))
            seen.add((week, col))

    if not refs:
        for m in _PAT_WEEK_EQ_VAL.finditer(source_text):
            week = m.group(1).upper()
            val = float(m.group(2).replace(",", ""))
            if (week, None) not in seen:
                refs.append(SourceRef(week=week, column=None, value=val))
                seen.add((week, None))

    for m in _PAT_COL_ARRAY.finditer(source_text):
        col = m.group(1).lower()
        vals = [float(v.strip()) for v in m.group(2).split(",") if v.strip()]
        for i, v in enumerate(vals):
            if i < len(_WEEKS_ORDERED):
                key = (_WEEKS_ORDERED[i], col)
                if key not in seen:
                    refs.append(SourceRef(week=_WEEKS_ORDERED[i], column=col, value=v))
                    seen.add(key)

    return refs


# ---------------------------------------------------------------------------
# Formula extraction: two response formats
# ---------------------------------------------------------------------------

def _extract_verified_fields(
    text: str,
) -> tuple[list[SourceRef], Optional[str], Optional[str]]:
    """Extract source_refs, formula_lhs, formula_rhs from a [VERIFIED] claim.

    Format A — Gemini inline parenthetical (single line):
        [VERIFIED] Text (source: W2 5100→W3 6200; calculation: (6200-5100)/5100 = 21.6%)

    Format B — Claude multi-line bullet (continuation lines):
        [VERIFIED] Text
        - Source: (a + b) / n = intermediate = result
        - Formula: (x - y) / y = step = **pct%**
        - Description: expr = result  (fallback: any bullet with '= number')
    """
    source_refs: list[SourceRef] = []
    formula_lhs = formula_rhs = None

    # ── Format A ──────────────────────────────────────────────────────────
    paren_m = _PAREN_RE.search(text)
    if paren_m:
        paren_content = paren_m.group(1)
        parts = _CALC_SPLIT_RE.split(paren_content, maxsplit=1)
        source_text = _SOURCE_PREFIX_RE.sub("", parts[0])
        source_refs = _parse_source_refs(source_text)
        if len(parts) > 1:
            formula_lhs, formula_rhs = _parse_calculation_multi(parts[1])

    # ── Format B: explicit "- Source:" / "- Formula:" bullet ─────────────
    if formula_lhs is None:
        for m in _BULLET_FORMULA_RE.finditer(text):
            lhs, rhs = _parse_calculation_multi(m.group(1))
            if lhs and rhs:
                formula_lhs, formula_rhs = lhs, rhs
                break

    # ── Format B fallback: any bullet line with "= <number>" ─────────────
    if formula_lhs is None:
        for m in _BULLET_EQ_RE.finditer(text):
            lhs, rhs = _parse_calculation_multi(m.group(0).lstrip("-* "))
            if lhs and rhs:
                formula_lhs, formula_rhs = lhs, rhs
                break

    # Source refs: try full claim text if Format A didn't find any
    if not source_refs:
        source_refs = _parse_source_refs(text)

    return source_refs, formula_lhs, formula_rhs


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_claims(response: str) -> list[Claim]:
    """Extract all labelled claims from a model response.

    Skips code blocks (``` fences). [VERIFIED] continuation lines (bullet
    details) are collected as part of the claim text for formula extraction.

    Args:
        response: Raw model response string.

    Returns:
        List of Claim objects in order of appearance.
    """
    claims: list[Claim] = []
    lines = response.splitlines()
    in_code_block = False
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            i += 1
            continue

        if in_code_block:
            i += 1
            continue

        m = _LABEL_RE.match(line)
        if not m:
            i += 1
            continue

        label = m.group(1).upper()
        full_text = m.group(2)

        # Collect continuation lines (until next label or blank line)
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if _LABEL_RE.match(nxt) or not nxt.strip():
                break
            full_text += "\n" + nxt.strip()
            j += 1

        if label == "VERIFIED":
            source_refs, formula_lhs, formula_rhs = _extract_verified_fields(full_text)
            parse_ok = formula_lhs is not None and formula_rhs is not None
            claims.append(Claim(
                label=label,
                text=full_text,
                source_refs=source_refs,
                formula_lhs=formula_lhs,
                formula_rhs=formula_rhs,
                parse_ok=parse_ok,
            ))
        else:
            claims.append(Claim(label=label, text=full_text))

        i = j

    return claims
