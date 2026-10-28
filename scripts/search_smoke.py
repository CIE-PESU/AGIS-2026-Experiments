"""Explicit live search checks with a neutral query; uses provider API credits."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def main():
    from dotenv import dotenv_values
    import httpx
    values = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    import os
    failed = False
    for name, url, headers, payload in [
        ("Serper", "https://google.serper.dev/search", {"X-API-KEY": os.getenv("SERPER_API_KEY") or values.get("SERPER_API_KEY", "")}, {"q": "example.com", "num": 1}),
        ("Tavily", "https://api.tavily.com/search", {}, {"api_key": os.getenv("TAVILY_API_KEY") or values.get("TAVILY_API_KEY", ""), "query": "example.com", "max_results": 1, "search_depth": "basic"}),
    ]:
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict) or result.get("error"):
                raise ValueError("Provider returned an error")
            print(f"{name}: authenticated search request succeeded")
        except Exception as exc:
            print(f"{name}: search check failed ({type(exc).__name__}); verify key, quota, and connectivity")
            failed = True
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
