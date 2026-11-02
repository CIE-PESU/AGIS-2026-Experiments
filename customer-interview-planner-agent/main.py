"""Standalone Discovery CLI. Real input is required unless --sample is explicit."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--input", type=Path, help="UTF-8 JSON file containing real founder inputs")
    choice.add_argument("--sample", action="store_true", help="Explicitly evaluate the demonstration example")
    args = parser.parse_args()
    from customer_interview_planner import run_discovery_analysis, SAMPLE_DISCOVERY_INPUTS
    inputs = SAMPLE_DISCOVERY_INPUTS if args.sample else json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(inputs, dict) or not inputs:
        parser.error("A non-empty founder input object is required.")
    if args.sample:
        print("DEMONSTRATION ONLY: synthetic example inputs; not a real customer assessment.")
    print(run_discovery_analysis(inputs).raw)


if __name__ == "__main__":
    main()
