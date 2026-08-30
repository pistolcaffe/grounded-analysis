import argparse
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grounded Analysis pipeline — run baseline/final agent and score results."
    )
    parser.add_argument(
        "--case",
        required=True,
        help="Case ID to run, e.g. 'case_01' (matches data/case_01_push.csv)",
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "final", "both"],
        default="both",
        help="Which prompt mode to run (default: both)",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="Number of times to repeat each run for consistency measurement (default: 3)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Case  : {args.case}")
    print(f"Mode  : {args.mode}")
    print(f"Repeat: {args.repeat}")

    # TODO: resolve data path from args.case (config.DATA_DIR / f"{args.case}_push.csv")
    # TODO: for each mode in (baseline / final based on args.mode):
    #         responses = [run_agent(data_path, prompt_path, model, provider)
    #                      for _ in range(args.repeat)]
    #         metrics_list = [score(r, raw_data) for r in responses]
    #         variance = consistency(responses, raw_data)
    #         append_changelog(...)
    #         save results to results/<case>_<mode>_<timestamp>.json
    # TODO: if mode == "both", print side-by-side comparison of baseline vs final metrics
    print("\n[TODO] Pipeline execution not yet implemented.")


if __name__ == "__main__":
    main()
