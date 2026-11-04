"""Compatibility rules for accounts created before development login was removed."""


def is_legacy_dev_student(user) -> bool:
    return (
        user.role == "student"
        and user.name == f"Dev User ({user.srn})"
        and not user.password_hash
        and not user.encrypted_password
    )


def mentor_advisor_type(user) -> str:
    # A provisioned mentor is a supervising account even with a local email alias.
    if user.srn.upper() in {"MENTOR1", "MENTOR2", "MENTOR3"} or (
        user.password_hash or user.encrypted_password
    ):
        return "faculty_mentor"
    return (
        "external_reviewer"
        if (user.email or "").lower().endswith("@agis.local")
        else "faculty_mentor"
    )
