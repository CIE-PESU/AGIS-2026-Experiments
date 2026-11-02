"""Read-only checks against an explicitly configured OpenAI-compatible server."""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlparse

import httpx


def is_local_endpoint(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    if hostname.lower() in {"localhost", "host.docker.internal", "host.containers.internal"}:
        return True
    try:
        address = ipaddress.ip_address(hostname)
        return address.is_loopback or address.is_private
    except ValueError:
        return False


def check_model_server(url: str, model: str, api_key: str = "", *, client=None) -> None:
    """List models only. Never starts a server, downloads or loads a model."""
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not parsed.path.rstrip("/").endswith("/v1")
    ):
        raise ValueError("LM_STUDIO_URL must be an HTTP(S) OpenAI-compatible URL ending in /v1.")
    if not model.startswith("openai/"):
        raise ValueError(
            "For an OpenAI-compatible local server, use OPENAI_MODEL_NAME=openai/<exact served model id>."
        )
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        response = (client or httpx).get(url.rstrip("/") + "/models", headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        available = {
            item["id"]
            for item in data["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(
            "Local LLM server is unavailable or returned an invalid model list. Check the configured address, authentication, and running server."
        ) from exc
    if model.removeprefix("openai/") not in available:
        raise RuntimeError(
            "The configured model is not offered by the local LLM server. Copy its exact model id from /v1/models; no substitute was selected."
        )


async def require_local_model() -> None:
    """Fail before claiming new work if a configured local model is unavailable."""
    import asyncio

    from core.config import settings
    from exceptions.base import LocalLLMUnavailableError

    if is_local_endpoint(settings.LM_STUDIO_URL):
        try:
            await asyncio.to_thread(
                check_model_server,
                settings.LM_STUDIO_URL,
                settings.OPENAI_MODEL_NAME,
                settings.OPENAI_API_KEY,
            )
        except (RuntimeError, ValueError) as exc:
            raise LocalLLMUnavailableError() from exc


def probe_local_generation(url: str, model: str, api_key: str) -> None:
    """Explicit inference probe: plain text, structured JSON and a harmless tool call."""
    import json

    from crewai import LLM

    llm = LLM(model=model, base_url=url, api_key=api_key, temperature=0, max_tokens=128, timeout=60)
    text = llm.call("Reply with the word OK only.")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The local model returned no text.")
    structured = llm.call(
        'Return a JSON object only, with the single boolean field "ok" set to true.'
    )
    if not isinstance(structured, str) or json.loads(structured) != {"ok": True}:
        raise ValueError("The local model did not return the requested structured JSON.")
    invoked = []

    def confirm():
        invoked.append(True)
        return "OK"

    # Provider tools are OpenAI JSON schemas; CrewAI's base-class annotation is narrower.
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "agis_probe",
                "description": "Confirm a local capability check; no side effects.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        }
    ]
    llm.call(
        "Call the agis_probe tool now, with no arguments. Do not just describe the tool.",
        tools=tools,
        available_functions={"agis_probe": confirm},
    )
    if not invoked:
        raise ValueError("The local model did not perform the requested tool call.")
