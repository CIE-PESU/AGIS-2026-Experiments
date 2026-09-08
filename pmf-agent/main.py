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
    result = run_pmf_analysis(SAMPLE_PMF_INPUTS)
    print("PMF Agent Result:")
    import json
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
