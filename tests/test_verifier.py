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

    # --- Per-claim parse detail ---
    print("\n=== VERIFIED CLAIM PARSE DETAIL ===")
    for i, c in enumerate(claims, 1):
        if c.label != "VERIFIED":
            continue
        preview = c.text[:70] + ("…" if len(c.text) > 70 else "")
        print(f"\n#{i} {preview}")
        print(f"   parse_ok   : {c.parse_ok}")
        print(f"   formula_lhs: {c.formula_lhs!r}")
        print(f"   formula_rhs: {c.formula_rhs!r}")
        print(f"   source_refs: {len(c.source_refs)} ref(s)")
        for ref in c.source_refs[:3]:
            print(f"     {ref}")
        if len(c.source_refs) > 3:
            print(f"     ... ({len(c.source_refs) - 3} more)")

    # --- Verification results ---
    results = verify_response(response, df)
    passed_count = sum(1 for r in results if r.passed)

    print("\n\n=== VERIFICATION RESULTS ===")
    for i, r in enumerate(results, 1):
        status = "PASS ✓" if r.passed else "FAIL ✗"
        preview = r.claim.text[:65] + ("…" if len(r.claim.text) > 65 else "")
        print(f"\n[{status}] #{i}: {preview}")
        print(f"  arithmetic_ok : {r.arithmetic_ok}")
        print(f"  source_ok     : {r.source_ok}")
        if r.expected is not None:
            print(f"  computed/got  : {r.expected:.4f} / {r.got}")
        if r.note != "ok":
            print(f"  note          : {r.note}")

    print("\n" + "=" * 60)
    print(f"FINAL: {passed_count}/{len(results)} PASSED")
    if passed_count < len(results):
        failed = [r for r in results if not r.passed]
        print(f"\nFailed claims:")
        for r in failed:
            print(f"  - {r.claim.text[:80]}…")
            print(f"    reason: {r.note}")


if __name__ == "__main__":
    main()
