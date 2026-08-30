import ast
import operator
import re
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

from verifier.parser import Claim, parse_claims

# Allowed AST node types for safe arithmetic evaluation
_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

TOLERANCE = 0.005  # 0.5% relative tolerance


# ---------------------------------------------------------------------------
# Safe arithmetic evaluator (no eval/exec)
# ---------------------------------------------------------------------------

def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"unsupported AST node: {type(node).__name__}")


def safe_eval_arithmetic(expr: str) -> float:
    """Evaluate a pure arithmetic expression using only +, -, *, /, parentheses.

    Strips thousands-separator commas before parsing.
    Raises ValueError for any non-arithmetic construct (names, calls, etc.).
    """
    cleaned = expr.strip().replace(",", "")
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"parse error in {expr!r}: {e}") from e
    return _eval_node(tree.body)


# ---------------------------------------------------------------------------
# RHS parsing
# ---------------------------------------------------------------------------

def _parse_rhs(rhs_str: str) -> tuple[float, bool]:
    """Return (numeric_value, is_percent) for an RHS string like '53.85%' or '46500'."""
    cleaned = rhs_str.strip().replace(",", "")
    is_percent = cleaned.endswith("%")
    if is_percent:
        cleaned = cleaned[:-1]
    try:
        return float(cleaned), is_percent
    except ValueError:
        raise ValueError(f"cannot parse RHS {rhs_str!r}")


def _within_tolerance(a: float, b: float, tol: float = TOLERANCE) -> bool:
    denom = max(abs(b), 1e-10)
    return abs(a - b) / denom <= tol


# ---------------------------------------------------------------------------
# VerifyResult
# ---------------------------------------------------------------------------

def _derive_status(arithmetic_ok: Any, source_ok: Any) -> str:
    """Map layer results to a three-way status string.

    "failed"  — at least one layer explicitly failed (wrong value or mismatch)
    "unknown" — no layer failed, but arithmetic could not be evaluated
    "passed"  — arithmetic confirmed correct; source confirmed or unparseable
    """
    if arithmetic_ok is False or source_ok is False:
        return "failed"
    if arithmetic_ok == "unknown":
        return "unknown"
    return "passed"


@dataclass
class VerifyResult:
    claim: Claim
    status: str                 # "passed" | "failed" | "unknown"
    arithmetic_ok: Any          # True | False | "unknown"
    source_ok: Any              # True | False | "unknown"
    expected: Optional[float]   # LHS evaluated (normalised to same scale as RHS)
    got: Optional[float]        # RHS numeric value
    note: str

    @property
    def passed(self) -> bool:
        return self.status == "passed"


# ---------------------------------------------------------------------------
# Layer A — arithmetic
# ---------------------------------------------------------------------------

def _check_arithmetic(claim: Claim) -> tuple[Any, Optional[float], Optional[float], list[str]]:
    notes: list[str] = []

    if not claim.parse_ok or claim.formula_lhs is None:
        notes.append("formula not parsed")
        return "unknown", None, None, notes

    try:
        rhs_val, is_percent = _parse_rhs(claim.formula_rhs)
    except ValueError as e:
        notes.append(f"rhs parse failed: {e}")
        return "unknown", None, None, notes

    try:
        lhs_val = safe_eval_arithmetic(claim.formula_lhs)
    except ValueError as e:
        notes.append(f"formula eval failed: {e}")
        return "unknown", None, rhs_val, notes

    expected = lhs_val * 100 if is_percent else lhs_val

    if _within_tolerance(expected, rhs_val):
        return True, expected, rhs_val, notes
    else:
        notes.append(
            f"arithmetic mismatch: computed {expected:.4f}, claimed {rhs_val}"
        )
        return False, expected, rhs_val, notes


# ---------------------------------------------------------------------------
# Layer B — source
# ---------------------------------------------------------------------------

def _check_source(claim: Claim, df: pd.DataFrame) -> tuple[Any, list[str]]:
    notes: list[str] = []

    if not claim.source_refs:
        notes.append("no source refs parsed")
        return "unknown", notes

    mismatches: list[str] = []
    unknowns: list[str] = []
    numeric_cols = df.select_dtypes(include="number").columns

    for ref in claim.source_refs:
        if ref.week is None or ref.value is None:
            unknowns.append(f"incomplete ref: {ref}")
            continue

        row = df[df["week"] == ref.week]
        if row.empty:
            mismatches.append(f"{ref.week} not found in data")
            continue

        if ref.column and ref.column in df.columns:
            actual = float(row[ref.column].iloc[0])
            if not _within_tolerance(ref.value, actual):
                mismatches.append(
                    f"{ref.week}.{ref.column}: claimed {ref.value}, actual {actual}"
                )
        else:
            # Column unknown — check if value appears in any numeric column
            row_vals = [float(row[c].iloc[0]) for c in numeric_cols]
            if any(_within_tolerance(ref.value, v) for v in row_vals):
                unknowns.append(f"{ref.week}={ref.value} found (column unspecified)")
            else:
                mismatches.append(
                    f"{ref.week}: value {ref.value} not found in any column"
                )

    if mismatches:
        notes.append("source mismatches: " + "; ".join(mismatches))
        return False, notes
    if unknowns:
        notes.append("partial source match: " + "; ".join(unknowns))
        return "unknown", notes
    return True, notes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_claim(claim: Claim, df: pd.DataFrame) -> VerifyResult:
    """Verify a [VERIFIED] claim in two independent layers.

    Layer A (arithmetic): evaluates formula_lhs with a safe AST-based evaluator
    and compares to formula_rhs within ±0.5% tolerance.

    Layer B (source): checks every (week, column, value) ref parsed from the
    source field against the raw DataFrame.

    Status rules:
      "passed"  — arithmetic confirmed correct; source confirmed or unparseable
      "failed"  — arithmetic wrong OR source value mismatches raw data
      "unknown" — no failure detected but arithmetic could not be evaluated
                  (e.g. Pearson correlation formula — outside arithmetic parser scope)

    Args:
        claim: A Claim with label == "VERIFIED".
        df: Original dataset as a DataFrame (must have a 'week' column).

    Returns:
        VerifyResult with status, per-layer breakdown, and diagnostic note.
    """
    arithmetic_ok, expected, got, a_notes = _check_arithmetic(claim)
    source_ok, s_notes = _check_source(claim, df)

    all_notes = a_notes + s_notes
    note = "; ".join(all_notes) if all_notes else "ok"

    return VerifyResult(
        claim=claim,
        status=_derive_status(arithmetic_ok, source_ok),
        arithmetic_ok=arithmetic_ok,
        source_ok=source_ok,
        expected=expected,
        got=got,
        note=note,
    )


def verify_response(response: str, df: pd.DataFrame) -> list[VerifyResult]:
    """Parse all claims in response and run verify_claim on each [VERIFIED] claim.

    Args:
        response: Raw model response string.
        df: Original dataset as a DataFrame.

    Returns:
        List of VerifyResult, one per [VERIFIED] claim, in order of appearance.
    """
    claims = parse_claims(response)
    return [verify_claim(c, df) for c in claims if c.label == "VERIFIED"]
