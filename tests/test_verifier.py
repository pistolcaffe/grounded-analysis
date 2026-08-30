#!/usr/bin/env python3
"""Test: parse + verify results/gemini_final_en.txt against data/case_01_push.csv."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from verifier.parser import parse_claims
from verifier.verifier import verify_response

ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "case_01_push.csv"
RESPONSE_PATH = ROOT / "results" / "gemini_final_en.txt"

_STATUS_ICON = {"passed": "PASS ✓", "failed": "FAIL ✗", "unknown": "UNKN ?"}


def main() -> None:
    response = RESPONSE_PATH.read_text(encoding="utf-8")
    df = pd.read_csv(DATA_PATH)

    # --- Parsing summary ---
    claims = parse_claims(response)
    label_counts: dict[str, int] = {}
    for c in claims:
        label_counts[c.label] = label_counts.get(c.label, 0) + 1

    print("=== PARSE SUMMARY ===")
    print(f"Total claims : {len(claims)}")
    for label in ("VERIFIED", "INFERENCE", "ASSUMPTION"):
        print(f"  [{label}] : {label_counts.get(label, 0)}")

    # --- Verification results ---
    results = verify_response(response, df)

    status_counts: dict[str, int] = {"passed": 0, "failed": 0, "unknown": 0}
    for r in results:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    print("\n\n=== VERIFICATION RESULTS ===")
    for i, r in enumerate(results, 1):
        icon = _STATUS_ICON.get(r.status, r.status)
        preview = r.claim.text[:65] + ("…" if len(r.claim.text) > 65 else "")
        print(f"\n[{icon}] #{i}: {preview}")
        print(f"  status        : {r.status}")
        print(f"  arithmetic_ok : {r.arithmetic_ok}")
        print(f"  source_ok     : {r.source_ok}")
        if r.expected is not None:
            print(f"  computed/got  : {r.expected:.4f} / {r.got}")
        if r.note != "ok":
            print(f"  note          : {r.note}")

    print("\n" + "=" * 60)
    print(f"TOTAL : {len(results)}")
    print(f"passed  : {status_counts['passed']}")
    print(f"failed  : {status_counts['failed']}")
    print(f"unknown : {status_counts['unknown']}")

    if status_counts["unknown"]:
        print("\nUnknown (outside evaluator scope):")
        for r in results:
            if r.status == "unknown":
                print(f"  - {r.claim.text[:80]}…")
                print(f"    reason: {r.note}")

    if status_counts["failed"]:
        print("\nFailed:")
        for r in results:
            if r.status == "failed":
                print(f"  - {r.claim.text[:80]}…")
                print(f"    reason: {r.note}")


if __name__ == "__main__":
    main()
