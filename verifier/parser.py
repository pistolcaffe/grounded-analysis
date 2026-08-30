from dataclasses import dataclass
from typing import Optional


@dataclass
class Claim:
    label: str          # "VERIFIED" | "INFERENCE" | "ASSUMPTION"
    text: str           # claim sentence (without the label prefix)
    source: Optional[str]       # raw values cited, e.g. "W2 5100 → W3 6200"
    calculation: Optional[str]  # formula cited, e.g. "(6200-5100)/5100 = 21.6%"


def parse_claims(response: str) -> list[Claim]:
    """Extract all labelled claims from a model response.

    Parses lines/blocks prefixed with [VERIFIED], [INFERENCE], or [ASSUMPTION] and splits out
    the inline source/calculation fields that [VERIFIED] claims are required to carry.

    Args:
        response: Raw model response string.

    Returns:
        List of Claim objects in order of appearance.
    """
    # TODO: use regex to find all [VERIFIED] / [INFERENCE] / [ASSUMPTION] prefixed claims
    # TODO: for [verified] claims, extract "source: ..." and "formula: ..." substrings
    #       into .source and .calculation fields
    # TODO: handle multi-line claims (claim continues until next label or blank line)
    raise NotImplementedError("parse_claims is not yet implemented")
