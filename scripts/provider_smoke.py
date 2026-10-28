"""Explicit live provider check: sends one tiny, non-sensitive prompt (may incur API usage)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def main():
    from core.config import settings
    from crewai import LLM
    llm = LLM(model=settings.OPENAI_MODEL_NAME, base_url=settings.LM_STUDIO_URL,
              api_key=settings.OPENAI_API_KEY, max_tokens=32, timeout=30, temperature=0,
              extra_body={"chat_template_kwargs": {"enable_thinking": False}}
                if settings.OPENAI_MODEL_NAME.endswith("nemotron-3.5-lightning-30b-a3b") else {})
    try:
        output = llm.call("Reply with the word OK only.")
    except Exception as exc:
        raise SystemExit(f"Live provider check failed ({type(exc).__name__}); verify endpoint, model entitlement, and credentials") from None
    if not isinstance(output, str) or not output.strip():
        raise SystemExit("Provider returned no text; verify model response configuration")
    print("Configured provider returned text through CrewAI successfully")


if __name__ == "__main__":
    main()
