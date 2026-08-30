import re
import statistics
from pathlib import Path
from typing import Any

import pandas as pd

from verifier.parser import parse_claims
from verifier.verifier import verify_response
from config import BASE_DIR

_LABEL_PREFIXES = {"VERIFIED", "INFERENCE", "ASSUMPTION"}
_LABEL_LINE_RE = re.compile(r"^\s*\[(VERIFIED|INFERENCE|ASSUMPTION)\]", re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_MIN_SENTENCE_LEN = 20  # chars; shorter fragments are noise


# ---------------------------------------------------------------------------
# Unlabeled sentence estimation (for baseline separation_rate denominator)
# ---------------------------------------------------------------------------

def _count_unlabeled_sentences(response: str, labeled_count: int) -> tuple[int, str]:
    """Estimate the number of unlabeled claim sentences in a response.

    Strips code blocks, then counts non-trivial sentences in remaining prose
    that are NOT already counted as labeled claims.

    Returns (unlabeled_count, method_note).
    """
    clean = _CODE_FENCE_RE.sub(" ", response)

    prose_lines = []
    for line in clean.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):               # markdown header
            continue
        if s.startswith("|"):               # table row
            continue
        if s.startswith(">"):               # blockquote (summary lines)
            continue
        if re.match(r"^[-*]\s", s):         # bullet sub-line (source/formula detail)
            continue
        if _LABEL_LINE_RE.match(s):         # labeled claim (already counted)
            continue
        prose_lines.append(s)

    raw_prose = " ".join(prose_lines)
    fragments = _SENTENCE_SPLIT_RE.split(raw_prose)
    sentences = [f.strip() for f in fragments if len(f.strip()) >= _MIN_SENTENCE_LEN]
    unlabeled = len(sentences)

    note = (
        f"unlabeled = sentences ≥{_MIN_SENTENCE_LEN} chars in non-code/non-header prose "
        f"(n={unlabeled}); labeled = {labeled_count}"
    )
    return unlabeled, note


# ---------------------------------------------------------------------------
# score()
# ---------------------------------------------------------------------------

def score(response: str, raw_data: pd.DataFrame) -> dict[str, Any]:
    """Compute grounding metrics for one agent response.

    Calls parse_claims() and verify_response() internally.

    Args:
        response: Raw model response string.
        raw_data: Original dataset as a DataFrame.

    Returns:
        Dict with keys:
          separation_rate  (float)  : labeled / (labeled + unlabeled)
          reverify_rate    (float|None) : passed / (passed + failed);
                                          None when no evaluatable [VERIFIED] claims
          unknown_count    (int)    : [VERIFIED] claims outside evaluator scope
          counts           (dict)   : raw breakdown by label and verify status
          note             (str)    : method note for separation denominator
    """
    claims = parse_claims(response)

    labeled = [c for c in claims if c.label in _LABEL_PREFIXES]
    labeled_count = len(labeled)

    counts_by_label = {lbl: 0 for lbl in _LABEL_PREFIXES}
    for c in labeled:
        counts_by_label[c.label] += 1

    unlabeled_count, count_note = _count_unlabeled_sentences(response, labeled_count)
    total_count = labeled_count + unlabeled_count

    separation_rate = labeled_count / total_count if total_count > 0 else 0.0

    verify_results = verify_response(response, raw_data)
    passed  = sum(1 for r in verify_results if r.status == "passed")
    failed  = sum(1 for r in verify_results if r.status == "failed")
    unknown = sum(1 for r in verify_results if r.status == "unknown")

    denom = passed + failed
    reverify_rate: float | None = (passed / denom) if denom > 0 else None

    return {
        "separation_rate": separation_rate,
        "reverify_rate": reverify_rate,
        "unknown_count": unknown,
        "counts": {
            "verified":   counts_by_label["VERIFIED"],
            "inference":  counts_by_label["INFERENCE"],
            "assumption": counts_by_label["ASSUMPTION"],
            "labeled":    labeled_count,
            "unlabeled":  unlabeled_count,
            "total":      total_count,
            "passed":     passed,
            "failed":     failed,
            "unknown":    unknown,
        },
        "note": count_note,
    }


# ---------------------------------------------------------------------------
# consistency()
# ---------------------------------------------------------------------------

def consistency(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure stability of metrics across multiple score() results.

    Baseline is expected to show high variance (non-deterministic labelling);
    final prompt is expected to converge (low variance).

    Args:
        results: List of dicts returned by score(), one per run.

    Returns:
        Dict with mean and stdev for separation_rate and reverify_rate,
        plus n (number of runs).
    """
    if len(results) < 2:
        return {"error": "need at least 2 results for consistency measurement", "n": len(results)}

    sep_rates = [r["separation_rate"] for r in results]
    rev_rates = [r["reverify_rate"] for r in results if r["reverify_rate"] is not None]

    out: dict[str, Any] = {
        "n": len(results),
        "separation_rate": {
            "mean":  statistics.mean(sep_rates),
            "stdev": statistics.stdev(sep_rates),
        },
    }

    if len(rev_rates) >= 2:
        out["reverify_rate"] = {
            "mean":  statistics.mean(rev_rates),
            "stdev": statistics.stdev(rev_rates),
        }
    elif rev_rates:
        out["reverify_rate"] = {"mean": rev_rates[0], "stdev": None}
    else:
        out["reverify_rate"] = None

    return out


# ---------------------------------------------------------------------------
# append_changelog()
# ---------------------------------------------------------------------------

def _fmt_rate(v: float | None) -> str:
    return f"{v * 100:.1f}%" if v is not None else "—"


def append_changelog(
    stage: str,
    tried: str,
    metrics: dict[str, Any],
    decision: str,
    changelog_path: Path = BASE_DIR / "CHANGELOG.md",
) -> None:
    """Append one row to the Improvement Changelog table in CHANGELOG.md.

    Args:
        stage:    Stage label (e.g. "Iteration 3", "Final").
        tried:    Brief description of what was attempted and why.
        metrics:  Dict from score() containing separation_rate and reverify_rate.
        decision: Outcome summary (kept / removed / learning note).
        changelog_path: Path to CHANGELOG.md (default: project root).
    """
    sep_str = _fmt_rate(metrics.get("separation_rate"))
    rev_str = _fmt_rate(metrics.get("reverify_rate"))
    unk = metrics.get("unknown_count", 0)
    evidence = f"separation {sep_str} / reverify {rev_str}"
    if unk:
        evidence += f" (unknown {unk})"

    new_row = f"| {stage} | {tried} | {evidence} | {decision} |"

    content = changelog_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Find the last markdown table row (| ... |) to insert after it
    last_table_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            last_table_idx = i

    if last_table_idx == -1:
        content = content.rstrip("\n") + f"\n{new_row}\n"
    else:
        lines.insert(last_table_idx + 1, new_row)
        content = "\n".join(lines) + "\n"

    changelog_path.write_text(content, encoding="utf-8")
