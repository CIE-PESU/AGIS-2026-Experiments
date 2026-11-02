"""Malformed/truthy error responses must never become authenticated profiles."""
import httpx
import pytest

from auth.pes_client import PESAuthClient
from exceptions.base import InvalidCredentialsError, PESAuthUnavailableError


@pytest.mark.parametrize("value", ["false", "true", "error", 1, 0, None])
async def test_only_explicit_authentication_success_is_accepted(monkeypatch, value):
    original = httpx.AsyncClient
    def factory(**kwargs):
        return original(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"status": value, "profile": {"srn": "PES2UG22CS001"}})), **kwargs)
    monkeypatch.setattr(httpx, "AsyncClient", factory)
    with pytest.raises(InvalidCredentialsError):
        await PESAuthClient().validate_credentials("PES2UG22CS001", "test-only")


async def test_mismatched_profile_cannot_create_another_identity(monkeypatch):
    original = httpx.AsyncClient
    def factory(**kwargs):
        return original(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"status": True, "profile": {"srn": "PES2UG22CS999"}})), **kwargs)
    monkeypatch.setattr(httpx, "AsyncClient", factory)
    with pytest.raises(PESAuthUnavailableError, match="different account"):
        await PESAuthClient().validate_credentials("PES2UG22CS001", "test-only")
