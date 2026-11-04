import pytest
from pydantic import ValidationError
from schemas.auth import LoginRequest


@pytest.mark.parametrize("role", ["admin", "mentor", "student"])
@pytest.mark.parametrize("number", [1, 2, 3])
def test_shared_usernames_are_accepted_and_normalized(role, number):
    request = LoginRequest(srn=f" {role}{number} ", password="valid-password")
    assert request.srn == f"{role.upper()}{number}"


@pytest.mark.parametrize("username", ["mentor4", "student4", "mentor1extra", "student"])
def test_other_non_pes_usernames_remain_invalid(username):
    with pytest.raises(ValidationError):
        LoginRequest(srn=username, password="valid-password")
