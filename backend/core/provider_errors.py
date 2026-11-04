"""Safe public diagnostics for provider failures, without exposing provider responses."""


def provider_failure(exc: Exception) -> tuple[int, str]:
    seen: set[int] = set()
    cause: BaseException | None = exc
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        status = getattr(cause, "status_code", None)
        if status is None:
            status = getattr(getattr(cause, "response", None), "status_code", None)
        name = type(cause).__name__
        if status in (401, 403) or name in {"AuthenticationError", "PermissionDeniedError"}:
            return (
                502,
                "The AI provider rejected authentication or model access. Check the backend's effective API key, endpoint, and model permissions.",
            )
        if status == 429 or name == "RateLimitError":
            return (
                503,
                "The AI provider reported a rate or quota limit. Check provider quota and retry later.",
            )
        if isinstance(cause, (TimeoutError, ConnectionError)) or name in {
            "APIConnectionError",
            "APITimeoutError",
            "ConnectError",
            "ConnectTimeout",
            "ReadTimeout",
        }:
            return (
                503,
                "The backend could not reach the AI provider in time. Check endpoint connectivity and retry.",
            )
        if isinstance(status, int) and status >= 500:
            return 503, "The AI provider is temporarily unavailable. Retry later."
        cause = cause.__cause__ or cause.__context__
    return (
        502,
        "The AI evaluation failed or returned an invalid result. Check the backend log for the failure type and verify model configuration.",
    )
