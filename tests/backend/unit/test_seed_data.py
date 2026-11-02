"""Reject ambiguous identities and inconsistent seed records before database writes."""

import pytest
from pydantic import ValidationError
from schemas.seed import SeedData

USER = {"id": "012345678901234567890123", "srn": " student ", "name": "Student", "role": "student"}


@pytest.mark.parametrize("extra", ["password_hash", "encrypted_password", "password"])
def test_seed_rejects_credentials(extra):
    with pytest.raises(ValidationError):
        SeedData(users=[{**USER, extra: "secret"}])


def test_seed_rejects_duplicate_normalized_identifiers():
    with pytest.raises(ValidationError, match="Duplicate SRNs"):
        SeedData(users=[USER, {**USER, "id": "112345678901234567890123", "srn": "STUDENT"}])


def test_seed_requires_stable_ids_and_preserves_absent_team_field():
    parsed = SeedData(users=[USER])
    assert parsed.users[0].srn == "STUDENT"
    assert "team_id" not in parsed.users[0].model_dump(exclude_unset=True)
    with pytest.raises(ValidationError):
        SeedData(users=[{**USER, "id": "invalid"}])


def test_seed_rejects_duplicate_team_members():
    with pytest.raises(ValidationError, match="duplicate members"):
        SeedData(
            teams=[
                {
                    "id": "012345678901234567890124",
                    "team_name": "Team",
                    "mentor_id": "",
                    "members": ["student", " STUDENT "],
                }
            ]
        )
