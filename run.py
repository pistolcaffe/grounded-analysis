import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import (
    DATA_DIR,
    DEFAULT_REPEAT,
    MODEL_NAME,
    MODEL_PROVIDER,
    RESULTS_DIR,
    ModelConfig,
)
from agent.runner import run_agent
from scorer.scorer import append_changelog, consistency, score
from verifier.verifier import verify_response


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Grounded Analysis pipeline — call the model, score responses, "
            "measure consistency.\n\n"
            "First run: use --repeat 1 to verify everything works before "
            "increasing repeat count."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--case", required=True,
        help="Case ID (e.g. 'case_01'). Matches data/case_01_*.csv",
    )
    parser.add_argument(
        "--mode", choices=["baseline", "final", "both"], default="both",
        help="Prompt mode to run (default: both)",
    )
    parser.add_argument(
        "--repeat", type=int, default=DEFAULT_REPEAT,
        help=f"Runs per mode for consistency measurement (default: {DEFAULT_REPEAT}). "
             "Start with 1 on first test.",
    )
    parser.add_argument(
        "--provider", default=MODEL_PROVIDER,
        help=f"Model provider: 'anthropic' or 'openai' (default: {MODEL_PROVIDER})",
    )
    parser.add_argument(
        "--model", default=MODEL_NAME,
        help=f"Model ID (default: {MODEL_NAME})",
    )
    parser.add_argument(
        "--write-changelog", action="store_true", default=False,
        help="Append the run's results to CHANGELOG.md (default: off — "
             "CHANGELOG.md is left untouched unless this is passed)",
    )
    parser.add_argument(
        "--show-response", action="store_true", default=False,
        help="Print each run's full response body to the terminal, just "
             "before its score summary (default: off)",
    )
    return parser.parse_args()


# ── Pipeline helpers ─────────────────────────────────────────────────────────

def _fmt(v: float | None, pct: bool = True) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}%" if pct else f"{v:.4f}"


_LABEL_COLORS = {
    "VERIFIED": "\033[32m",    # green
    "INFERENCE": "\033[33m",   # yellow
    "ASSUMPTION": "\033[31m",  # red
}
_LABEL_RESET = "\033[0m"
_LABEL_RE = re.compile(r"\[(VERIFIED|INFERENCE|ASSUMPTION)\]")


def _highlight_labels(text: str) -> str:
    return _LABEL_RE.sub(
        lambda m: f"{_LABEL_COLORS[m.group(1)]}[{m.group(1)}]{_LABEL_RESET}",
        text,
    )


def _print_response(response: str) -> None:
    print(f"\n  {'┄' * 53}")
    print(_highlight_labels(response))
    print(f"  {'┄' * 53}")


_STATUS_COLORS = {
    "passed": "\033[32m",   # green
    "failed": "\033[31m",   # red
    "unknown": "\033[33m",  # yellow
}


def _print_verification(verify_results: list) -> None:
    counts = {"passed": 0, "failed": 0, "unknown": 0}

    print("\n  === Independent verifier ===")
    for r in verify_results:
        counts[r.status] += 1
        summary = r.claim.text.splitlines()[0].strip()
        color = _STATUS_COLORS.get(r.status, "")
        print(f"  [{color}{r.status:<7}{_LABEL_RESET}] {summary}")

    print(
        f"  Verifier: passed {counts['passed']} / "
        f"failed {counts['failed']} / unknown {counts['unknown']}"
    )


def _run_mode(
    case_id: str,
    mode: str,
    repeat: int,
    model_config: ModelConfig,
    df: pd.DataFrame,
    show_response: bool = False,
) -> tuple[list[dict], list[str]]:
    """Run one mode `repeat` times. Returns (metrics_list, responses)."""
    metrics_list: list[dict] = []
    responses: list[str] = []

    print(f"\n{'─' * 55}")
    print(f"  {case_id} | {mode.upper()} | {model_config.provider}/{model_config.model}")
    print(f"  repeat={repeat}")
    print(f"{'─' * 55}")

    for i in range(1, repeat + 1):
        print(f"\n  [Run {i}/{repeat}]")
        response = run_agent(case_id, mode, model_config)
        metrics = score(response, df)
        responses.append(response)
        metrics_list.append(metrics)

        if show_response:
            _print_response(response)
            _print_verification(verify_response(response, df))

        sep = _fmt(metrics["separation_rate"])
        rev = _fmt(metrics["reverify_rate"])
        unk = metrics["unknown_count"]
        print(f"  → separation={sep}  reverify={rev}  unknown={unk}")

    return metrics_list, responses


def _print_summary(mode: str, metrics_list: list[dict]) -> None:
    n = len(metrics_list)
    print(f"\n  Summary ({mode}, n={n}):")

    sep_vals = [m["separation_rate"] for m in metrics_list]
    rev_vals = [m["reverify_rate"] for m in metrics_list if m["reverify_rate"] is not None]

    if n == 1:
        print(f"    separation_rate : {_fmt(sep_vals[0])}")
        print(f"    reverify_rate   : {_fmt(rev_vals[0]) if rev_vals else 'N/A'}")
        print(f"    unknown_count   : {metrics_list[0]['unknown_count']}")
    else:
        con = consistency(metrics_list)
        sep_c = con["separation_rate"]
        print(f"    separation_rate : mean={_fmt(sep_c['mean'])}  stdev={sep_c['stdev']:.4f}")
        rev_c = con.get("reverify_rate")
        if rev_c and rev_c.get("stdev") is not None:
            print(f"    reverify_rate   : mean={_fmt(rev_c['mean'])}  stdev={rev_c['stdev']:.4f}")
        elif rev_c:
            print(f"    reverify_rate   : mean={_fmt(rev_c['mean'])}  stdev=N/A (n<2 valid runs)")
        else:
            print(f"    reverify_rate   : N/A")
        print(f"    unknown_count   : {metrics_list[0]['unknown_count']}")


def _print_comparison(
    baseline_metrics: list[dict],
    final_metrics: list[dict],
) -> None:
    b = baseline_metrics[0]
    f = final_metrics[0]

    def delta(bv: float | None, fv: float | None) -> str:
        if bv is None or fv is None:
            return ""
        diff = (fv - bv) * 100
        sign = "+" if diff >= 0 else ""
        return f"  ({sign}{diff:.1f}pp)"

    b_sep = b["separation_rate"]
    f_sep = f["separation_rate"]
    b_rev = b["reverify_rate"]
    f_rev = f["reverify_rate"]

    print(f"\n{'═' * 55}")
    print("  COMPARISON  baseline → final")
    print(f"{'═' * 55}")
    print(f"  separation_rate : {_fmt(b_sep):>7}  →  {_fmt(f_sep):>7}{delta(b_sep, f_sep)}")
    print(f"  reverify_rate   : {_fmt(b_rev):>7}  →  {_fmt(f_rev):>7}{delta(b_rev, f_rev)}")
    print(f"  unknown_count   : {b['unknown_count']:>7}  →  {f['unknown_count']:>7}")


def _save_results(case_id: str, mode: str, metrics_list: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{case_id}_{mode}_{ts}.json"
    out_path.write_text(
        json.dumps(
            {"case_id": case_id, "mode": mode, "timestamp": ts, "runs": metrics_list},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  Results saved → results/{out_path.name}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    model_config = ModelConfig(
        provider=args.provider,
        model=args.model,
    )

    # Resolve data file
    data_files = sorted(DATA_DIR.glob(f"{args.case}_*.csv"))
    if not data_files:
        sys.exit(f"Error: no CSV found for '{args.case}' in {DATA_DIR}")
    df = pd.read_csv(data_files[0])

    modes = ["baseline", "final"] if args.mode == "both" else [args.mode]
    all_metrics: dict[str, list[dict]] = {}

    for mode in modes:
        metrics_list, _ = _run_mode(
            args.case, mode, args.repeat, model_config, df,
            show_response=args.show_response,
        )
        all_metrics[mode] = metrics_list
        _print_summary(mode, metrics_list)
        _save_results(args.case, mode, metrics_list)

    if args.mode == "both":
        _print_comparison(all_metrics["baseline"], all_metrics["final"])

    # Append to CHANGELOG only when explicitly requested
    if args.write_changelog:
        for mode, metrics_list in all_metrics.items():
            last = metrics_list[-1]
            append_changelog(
                stage=f"auto — {args.case}/{mode}",
                tried=f"repeat={args.repeat}, {model_config.provider}/{model_config.model}",
                metrics=last,
                decision="(fill in manually)",
            )
        print("\n  CHANGELOG.md updated.")

    print()


if __name__ == "__main__":
    main()
