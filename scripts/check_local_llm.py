"""Check the configured local model; --generate also checks text, JSON and tool calling through CrewAI."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from core.llm_provider import check_model_server, is_local_endpoint, probe_local_generation
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Send three non-sensitive capability probes through CrewAI",
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", encoding="utf-8-sig")
    url = os.getenv("LM_STUDIO_URL", "")
    model = os.getenv("OPENAI_MODEL_NAME", "")
    key = os.getenv("OPENAI_API_KEY", "lm-studio")
    if not is_local_endpoint(url):
        raise SystemExit(
            "This check requires a configured loopback/private local LLM endpoint; it will not contact a cloud provider."
        )
    try:
        check_model_server(url, model, key)
        print(
            "Read-only model-list check passed for the exact requested model; no server/model load was requested."
        )
        if args.generate:
            probe_local_generation(url, model, key)
            print(
                "Local model passed text, JSON, and harmless tool-calling checks through CrewAI. No database records were created."
            )
    except Exception as exc:
        print(
            f"Local model check failed: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
