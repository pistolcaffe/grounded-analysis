from pathlib import Path
from typing import Any
import pandas as pd

from verifier.parser import parse_claims
from verifier.verifier import verify_response
from config import BASE_DIR


def score(response: str, raw_data: pd.DataFrame) -> dict[str, Any]:
    """Compute separation_rate, reverify_rate, and related metrics for one response.

    Args:
        response: Raw model response string.
        raw_data: The original dataset as a DataFrame.

    Returns:
        Dict with keys:
          - separation_rate (float): labelled claims / total claims
          - reverify_rate (float): verifier-passed [verified] claims / total [verified] claims
          - total_claims (int)
          - labelled_claims (int)
          - verified_claims (int)
          - verified_passed (int)
    """
    # TODO: call parse_claims(response) to count total vs labelled claims
    # TODO: call verify_response(response, raw_data) to get pass/fail per [verified] claim
    # TODO: compute separation_rate = labelled / total
    # TODO: compute reverify_rate = passed / total [verified]
    # TODO: return full metrics dict
    raise NotImplementedError("score is not yet implemented")


def consistency(responses: list[str], raw_data: pd.DataFrame) -> dict[str, float]:
    """Measure variance of key metrics across multiple runs of the same prompt.

    Args:
        responses: List of raw model response strings (same prompt, repeated runs).
        raw_data: The original dataset as a DataFrame.

    Returns:
        Dict with variance of separation_rate and reverify_rate across responses.
    """
    # TODO: call score() for each response
    # TODO: compute variance (stdev) of separation_rate and reverify_rate
    # TODO: return {"separation_rate_var": ..., "reverify_rate_var": ...}
    raise NotImplementedError("consistency is not yet implemented")


def append_changelog(
    iteration_name: str,
    tried: str,
    metrics: dict[str, Any],
    decision: str,
    changelog_path: Path = BASE_DIR / "CHANGELOG.md",
) -> None:
    """Append one row to the Improvement Changelog table.

    Args:
        iteration_name: Label for this run (e.g. "Iteration 3").
        tried: Brief description of what was attempted and why.
        metrics: Dict containing at least separation_rate and reverify_rate.
        decision: Outcome summary (kept / removed / learning).
        changelog_path: Path to CHANGELOG.md.
    """
    # TODO: format metrics into "separation X% / reverify Y%" string
    # TODO: append "| iteration_name | tried | metrics_str | decision |" row to
    #       the markdown table in changelog_path
    raise NotImplementedError("append_changelog is not yet implemented")
