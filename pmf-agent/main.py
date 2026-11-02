"""
main.py — PMF Agent Entrypoint
"""

from pmf_analyzer import run_pmf_analysis

SAMPLE_PMF_INPUTS = {
    "idea_name": "PharmaTrace ERP Traceability",
    "problem_statement": "Counterfeit medicines threaten supply chain integrity and distributor liability.",
    "proposed_solution": "Parent-child QR verification platform integrated directly into ERP systems.",
    "customer_segment": "Pharmaceutical distributors and manufacturers"
}

def main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Evaluate real PMF inputs, or an explicitly requested demo.")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--input", type=Path, help="UTF-8 JSON founder evidence file")
    choice.add_argument("--sample", action="store_true", help="Explicitly evaluate synthetic example inputs")
    args = parser.parse_args()
    inputs = SAMPLE_PMF_INPUTS if args.sample else json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(inputs, dict) or not inputs:
        parser.error("A non-empty founder input object is required.")
    if args.sample:
        print("DEMONSTRATION ONLY: synthetic example inputs; no measured customer evidence.")
    result = run_pmf_analysis(inputs)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
