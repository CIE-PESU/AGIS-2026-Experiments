from customer_interview_planner import (
    run_discovery_analysis,
    SAMPLE_DISCOVERY_INPUTS,
)


def main():
    result = run_discovery_analysis(SAMPLE_DISCOVERY_INPUTS)
    print(result.raw)


if __name__ == "__main__":
    main()