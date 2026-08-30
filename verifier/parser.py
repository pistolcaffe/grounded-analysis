from dataclasses import dataclass
from typing import Optional


@dataclass
class Claim:
    label: str          # "검증됨" | "추론" | "가정"
    text: str           # claim sentence (without the label prefix)
    source: Optional[str]       # raw values cited, e.g. "W2 5100 → W3 6200"
    calculation: Optional[str]  # formula cited, e.g. "(6200-5100)/5100 = 21.6%"


def parse_claims(response: str) -> list[Claim]:
    """Extract all labelled claims from a model response.

    Parses lines/blocks prefixed with [검증됨], [추론], or [가정] and splits out
    the inline source/calculation fields that [검증됨] claims are required to carry.

    Args:
        response: Raw model response string.

    Returns:
        List of Claim objects in order of appearance.
    """
    # TODO: use regex to find all [검증됨] / [추론] / [가정] prefixed claims
    # TODO: for [검증됨] claims, extract "원본: ..." and "계산: ..." substrings
    #       into .source and .calculation fields
    # TODO: handle multi-line claims (claim continues until next label or blank line)
    raise NotImplementedError("parse_claims is not yet implemented")
