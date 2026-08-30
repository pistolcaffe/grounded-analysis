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


@dataclass
class SourceRef:
    week: Optional[str]
    column: Optional[str]
    value: Optional[float]

    def __str__(self) -> str:
        parts = [p for p in [self.week, self.column, str(self.value) if self.value is not None else None] if p]
        return " ".join(parts)


@dataclass
class Claim:
    label: str                              # VERIFIED | INFERENCE | ASSUMPTION
    text: str                               # full text after the label prefix
    source_refs: list[SourceRef] = field(default_factory=list)
    formula_lhs: Optional[str] = None      # left side of "LHS = RHS"
    formula_rhs: Optional[str] = None      # right side (the claimed result)
    parse_ok: bool = True                   # False when formula extraction failed


def _parse_source_refs(source_text: str) -> list[SourceRef]:
    refs: list[SourceRef] = []
    seen: set[tuple] = set()

    # Pattern 1: "W{n} {column} {value}"  e.g. "W2 push_sent 5200"
    for m in _PAT_WEEK_COL_VAL.finditer(source_text):
        week = m.group(1).upper()
        col = m.group(2).lower()
        val = float(m.group(3).replace(",", ""))
        key = (week, col)
        if key not in seen:
            refs.append(SourceRef(week=week, column=col, value=val))
            seen.add(key)

    # Pattern 2: "W{n}={value}"  e.g. "W1=4800" — only when pattern 1 found nothing
    if not refs:
        for m in _PAT_WEEK_EQ_VAL.finditer(source_text):
            week = m.group(1).upper()
            val = float(m.group(2).replace(",", ""))
            key = (week, None)
            if key not in seen:
                refs.append(SourceRef(week=week, column=None, value=val))
                seen.add(key)

    # Pattern 3: "{column} array [v1, v2, ...]"  — always checked (Pearson claims)
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


def _parse_calculation(calc_text: str) -> tuple[Optional[str], Optional[str]]:
    """Split 'LHS = RHS' on the last '=' sign."""
    calc_text = calc_text.strip()
    idx = calc_text.rfind("=")
    if idx == -1:
        return None, None
    lhs = calc_text[:idx].strip()
    rhs = calc_text[idx + 1:].strip()
    return (lhs or None), (rhs or None)


def _extract_verified_fields(
    text: str,
) -> tuple[list[SourceRef], Optional[str], Optional[str]]:
    """Pull source_refs, formula_lhs, formula_rhs out of a [VERIFIED] claim."""
    paren_m = _PAREN_RE.search(text)
    if not paren_m:
        return [], None, None

    paren_content = paren_m.group(1)
    parts = _CALC_SPLIT_RE.split(paren_content, maxsplit=1)

    source_text = _SOURCE_PREFIX_RE.sub("", parts[0])
    source_refs = _parse_source_refs(source_text)

    formula_lhs = formula_rhs = None
    if len(parts) > 1:
        formula_lhs, formula_rhs = _parse_calculation(parts[1])

    return source_refs, formula_lhs, formula_rhs


def parse_claims(response: str) -> list[Claim]:
    """Extract all labelled claims from a model response.

    Skips code blocks (``` fences) and bare table/header lines.
    Non-[VERIFIED] claims get label + text only.
    [VERIFIED] claims get source_refs, formula_lhs, formula_rhs.
    Claims whose formula cannot be extracted have parse_ok=False but are kept.

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
            full_text += " " + nxt.strip()
            j += 1

        if label == "VERIFIED":
            source_refs, formula_lhs, formula_rhs = _extract_verified_fields(full_text)
            parse_ok = formula_lhs is not None and formula_rhs is not None
            claims.append(
                Claim(
                    label=label,
                    text=full_text,
                    source_refs=source_refs,
                    formula_lhs=formula_lhs,
                    formula_rhs=formula_rhs,
                    parse_ok=parse_ok,
                )
            )
        else:
            claims.append(Claim(label=label, text=full_text))

        i = j

    return claims
