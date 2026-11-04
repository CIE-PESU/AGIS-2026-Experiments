from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from core.account_policy import is_legacy_dev_student, mentor_advisor_type
from fastapi import HTTPException


def account(**overrides):
    return SimpleNamespace(
        srn="PES2UG22CS098",
        name="Dev User (PES2UG22CS098)",
        role="student",
        password_hash=None,
        encrypted_password=None,
        email=None,
        team_id=None,
        **overrides,
    )


@pytest.mark.parametrize("srn", ["MENTOR1", "MENTOR2", "MENTOR3"])
def test_shared_mentors_are_supervisors_with_local_email(srn):
    user = account()
    user.srn, user.role, user.email = srn, "mentor", f"{srn.lower()}@agis.local"
    assert mentor_advisor_type(user) == "faculty_mentor"


def test_actual_external_reviewer_stays_external():
    user = account()
    user.srn, user.role, user.email = "REVIEWER@AGIS.LOCAL", "mentor", "reviewer@agis.local"
    assert mentor_advisor_type(user) == "external_reviewer"
    user.password_hash = "provisioned-hash"
    assert mentor_advisor_type(user) == "faculty_mentor"


def test_legacy_placeholder_detection_preserves_real_and_provisioned_students():
    user = account()
    assert is_legacy_dev_student(user)
    user.name = "Real Student"
    assert not is_legacy_dev_student(user)
    user.name = f"Dev User ({user.srn})"
    user.password_hash = "provisioned-hash"
    assert not is_legacy_dev_student(user)


async def test_legacy_placeholder_cannot_be_newly_allocated_but_existing_membership_is_preserved(
    monkeypatch,
):
    from routes.v1 import admin

    user = account()
    monkeypatch.setattr(
        admin,
        "User",
        SimpleNamespace(find=lambda *_: SimpleNamespace(to_list=AsyncMock(return_value=[user]))),
    )
    req = admin.TeamCreateRequest(name="Team", members=[user.srn])
    with pytest.raises(HTTPException) as error:
        await admin.validate_team_references(req)
    assert error.value.status_code == 422
    user.team_id = "existing-team"
    await admin.validate_team_references(req, team_id="existing-team")
