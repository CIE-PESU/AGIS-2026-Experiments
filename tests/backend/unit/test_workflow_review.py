"""Regression coverage for clone setup, scoped lookups and actionable provider failures."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from bson import ObjectId
from core.provider_errors import provider_failure
from core.security import verify_password
from database.branch_accounts import provision_branch_accounts
from schemas.auth import CurrentUser


async def test_provisioning_uses_seed_ids_and_valid_passwords():
    database = SimpleNamespace(users=SimpleNamespace(update_one=AsyncMock()))
    await provision_branch_accounts(database)
    all_calls = database.users.update_one.await_args_list
    calls = [call for call in all_calls if "$setOnInsert" in call.args[1]]
    assert len(calls) == 9
    repairs = [call for call in all_calls if "$set" in call.args[1]]
    assert len(repairs) == 9
    for call in repairs:
        assert call.args[0]["password_hash"] is None
        assert call.args[0]["encrypted_password"] is None
    seed = json.loads(Path("backend/scripts/seed_data.json").read_text())
    ids = {user["srn"]: ObjectId(user["id"]) for user in seed["users"]}
    expected = {f"{role}{i}" for role in ("ADMIN", "MENTOR", "STUDENT") for i in (1, 2, 3)}
    assert set(ids) == expected
    assert {call.args[0]["srn"] for call in calls} == expected
    prefixes = {"admin": "aerodactyl", "mentor": "mosasaur", "student": "stegosaur"}
    for call in calls:
        query, update = call.args
        assert set(update) == {"$setOnInsert"}
        account = update["$setOnInsert"]
        assert verify_password(
            prefixes[account["role"]] + query["srn"][-1], account["password_hash"]
        )
        if query["srn"] in ids:
            assert account["_id"] == ids[query["srn"]]


async def test_active_session_lookup_hides_unassigned_team(monkeypatch):
    from exceptions.base import SessionNotFoundError
    from routes.v1 import sessions
    from services import session_service

    raw = SimpleNamespace(id="507f1f77bcf86cd799439011", team_id="other-team")
    repo = SimpleNamespace(
        find_active_by_student=AsyncMock(return_value=raw),
        find_by_id=AsyncMock(return_value=raw),
    )
    monkeypatch.setattr(sessions, "session_repo", repo)
    monkeypatch.setattr(session_service, "session_repo", repo)
    caller = CurrentUser(user_id="mentor", role="mentor", mentor_team_ids=["assigned-team"])
    with pytest.raises(SessionNotFoundError):
        await sessions.get_active_session_by_user(None, "student", caller)


@pytest.mark.parametrize(
    "status,expected_code,phrase",
    [
        (401, 502, "authentication"),
        (403, 502, "authentication"),
        (429, 503, "quota"),
        (503, 503, "temporarily unavailable"),
    ],
)
def test_provider_errors_survive_agent_wrapping_without_exposing_response(
    status, expected_code, phrase
):
    request = httpx.Request("POST", "https://provider.test/v1")
    original = httpx.HTTPStatusError(
        "SECRET KEY AND RESPONSE", request=request, response=httpx.Response(status, request=request)
    )
    wrapped = RuntimeError("agent failed")
    wrapped.__cause__ = original
    code, message = provider_failure(wrapped)
    assert code == expected_code and phrase in message
    assert "SECRET" not in message


def test_invalid_output_and_connection_failures_are_distinguished():
    assert provider_failure(ValueError("bad json"))[0] == 502
    assert provider_failure(ConnectionError("unreachable"))[0] == 503


@pytest.mark.parametrize("role", ["admin", "mentor"])
async def test_dashboard_roles_cannot_invoke_quickstart(monkeypatch, role):
    from dependencies.auth import get_current_user
    from exceptions.base import InsufficientPermissionsError
    from fastapi import FastAPI
    from routes.v1 import quickstart

    app = FastAPI()
    app.include_router(quickstart.router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id="test", role=role)
    agent = AsyncMock()
    monkeypatch.setattr(quickstart, "run_quickstart_agent", agent)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        with pytest.raises(InsufficientPermissionsError):
            await client.post(
                "/quickstart/evaluate",
                json={
                    key: "test"
                    for key in [
                        "problem",
                        "customer",
                        "solution",
                        "consequence",
                        "business_model",
                        "urgency",
                        "hurdles",
                    ]
                },
            )
    agent.assert_not_awaited()
