from typing import Any
import pandas as pd

from verifier.parser import Claim, parse_claims


def verify_claim(claim: Claim, raw_data: pd.DataFrame) -> dict[str, Any]:
    """Independently recompute a [VERIFIED] claim and compare against the cited value.

    This is the core anti-self-reference check: the calculation is re-derived from
    raw_data by deterministic code, not by trusting the agent's own arithmetic.

    Args:
        claim: A Claim with label == "VERIFIED" and non-empty source/calculation.
        raw_data: The original dataset as a DataFrame.

    Returns:
        Dict with keys:
          - passed (bool): True if recomputed value matches the claim.
          - expected: Value the agent claimed.
          - got: Value this verifier independently computed.
          - reason (str): Human-readable explanation on mismatch.
    """
    # TODO: parse claim.source to identify which rows/columns to pull from raw_data
    # TODO: parse claim.calculation to determine the operation (%, delta, sum, …)
    # TODO: recompute the result independently using pandas
    # TODO: compare recomputed value to claimed value within a tolerance
    # TODO: return {passed, expected, got, reason}
    raise NotImplementedError("verify_claim is not yet implemented")


def verify_response(response: str, raw_data: pd.DataFrame) -> list[dict[str, Any]]:
    """Parse all claims in a response and verify every [VERIFIED] claim.

    Args:
        response: Raw model response string.
        raw_data: The original dataset as a DataFrame.

    Returns:
        List of verification result dicts (one per [verified] claim).
    """
    # TODO: call parse_claims(response) to get all claims
    # TODO: filter to label == "VERIFIED" and call verify_claim for each
    # TODO: return list of result dicts
    raise NotImplementedError("verify_response is not yet implemented")
