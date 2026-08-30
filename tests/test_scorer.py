#!/usr/bin/env python3
"""Test scorer against the final and a synthetic baseline response."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from scorer.scorer import append_changelog, consistency, score

ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "case_01_push.csv"
FINAL_RESPONSE_PATH = ROOT / "results" / "gemini_final_en.txt"

# Synthetic baseline: no labels, causation asserted, no formulas
BASELINE_SAMPLE = """\
The data shows weekly app metrics over 8 weeks.
Push notifications ranged from 5,000 to 9,100 per week.
Weeks 3, 4, 7, and 8 had noticeably higher push volumes, which drove user growth.
Active users peaked at 4,250 in week 8, reflecting the impact of the push campaigns.
Revenue was highest in weeks 7 and 8 at 6,900 and 7,000 respectively, clearly caused by the increased push activity.
Support tickets also rose sharply during high-push weeks, reaching 95 and 98, proving that more pushes increase customer inquiries.
There is a strong correlation between push sent and revenue across the entire period.
The average weekly active users over the 8-week period was approximately 3,694.
Overall, the data clearly demonstrates that push notifications are the primary driver of both revenue and support ticket volume.
Increasing push volume to 10,000 per week should yield further revenue gains.
"""


def _print_score(label: str, m: dict) -> None:
    c = m["counts"]
    sep = m["separation_rate"]
    rev = m["reverify_rate"]
    unk = m["unknown_count"]

    print(f"\n{'=' * 55}")
    print(f"  {label}")
    print(f"{'=' * 55}")
    print(f"  separation_rate : {sep * 100:.1f}%")
    print(f"  reverify_rate   : {rev * 100:.1f}%" if rev is not None else "  reverify_rate   : — (no evaluatable claims)")
    print(f"  unknown_count   : {unk}")
    print(f"  counts          :")
    print(f"    [VERIFIED]    : {c['verified']}")
    print(f"    [INFERENCE]   : {c['inference']}")
    print(f"    [ASSUMPTION]  : {c['assumption']}")
    print(f"    unlabeled     : {c['unlabeled']}")
    print(f"    total         : {c['total']}")
    print(f"    passed        : {c['passed']}")
    print(f"    failed        : {c['failed']}")
    print(f"    unknown       : {c['unknown']}")
    print(f"  note            : {m['note']}")


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    # ── Test 1: Final response ──────────────────────────────────────────────
    final_response = FINAL_RESPONSE_PATH.read_text(encoding="utf-8")
    final_metrics = score(final_response, df)
    _print_score("FINAL (gemini_final_en.txt)", final_metrics)

    # Assertions
    assert final_metrics["separation_rate"] > 0.90, (
        f"Expected separation_rate > 90%, got {final_metrics['separation_rate']:.2%}"
    )
    assert final_metrics["reverify_rate"] == 1.0, (
        f"Expected reverify_rate == 100%, got {final_metrics['reverify_rate']}"
    )
    assert final_metrics["unknown_count"] == 2, (
        f"Expected unknown_count == 2 (Pearson), got {final_metrics['unknown_count']}"
    )
    print("\n  ✓ All FINAL assertions passed")

    # ── Test 2: Baseline sample ─────────────────────────────────────────────
    baseline_metrics = score(BASELINE_SAMPLE, df)
    _print_score("BASELINE (synthetic sample)", baseline_metrics)

    assert baseline_metrics["separation_rate"] < 0.10, (
        f"Expected separation_rate < 10% for baseline, got {baseline_metrics['separation_rate']:.2%}"
    )
    assert baseline_metrics["counts"]["labeled"] == 0, (
        f"Expected 0 labeled claims in baseline, got {baseline_metrics['counts']['labeled']}"
    )
    print("\n  ✓ All BASELINE assertions passed")

    # ── Test 3: consistency() ───────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print("  CONSISTENCY (simulated 3 runs with slight variance)")
    print(f"{'=' * 55}")

    # Simulate 3 runs with slight metric noise (real runs would call the API)
    import copy, random
    random.seed(42)
    simulated_finals = []
    for _ in range(3):
        m = copy.deepcopy(final_metrics)
        # Small jitter to simulate non-determinism
        m["separation_rate"] = min(1.0, m["separation_rate"] + random.uniform(-0.02, 0.02))
        simulated_finals.append(m)

    simulated_baselines = []
    for _ in range(3):
        m = copy.deepcopy(baseline_metrics)
        m["separation_rate"] = max(0.0, m["separation_rate"] + random.uniform(-0.05, 0.05))
        simulated_baselines.append(m)

    final_consistency = consistency(simulated_finals)
    baseline_consistency = consistency(simulated_baselines)

    print(f"\n  Final   sep stdev : {final_consistency['separation_rate']['stdev']:.4f}")
    print(f"  Baseline sep stdev: {baseline_consistency['separation_rate']['stdev']:.4f}")
    print(f"  (Final stdev is expected to be low — prompt is deterministic)")

    # ── Test 4: append_changelog() ──────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print("  CHANGELOG append (dry-run to a temp file)")
    print(f"{'=' * 55}")

    import tempfile, shutil
    tmp = Path(tempfile.mktemp(suffix=".md"))
    shutil.copy(ROOT / "CHANGELOG.md", tmp)

    try:
        append_changelog(
            stage="Test Run",
            tried="scorer unit test — verifying append_changelog()",
            metrics=final_metrics,
            decision="Test only — not a real iteration",
            changelog_path=tmp,
        )
        written = tmp.read_text(encoding="utf-8")
        assert "Test Run" in written, "New row not found in CHANGELOG"
        last_table_row = [l for l in written.splitlines() if l.strip().startswith("|")][-1]
        print(f"\n  Appended row:\n  {last_table_row}")
        print("\n  ✓ append_changelog assertion passed")
    finally:
        tmp.unlink(missing_ok=True)

    print(f"\n{'=' * 55}")
    print("  ALL TESTS PASSED")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
