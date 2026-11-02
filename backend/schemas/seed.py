"""Validated, credential-free account metadata used by the seed importer."""

from datetime import datetime
from typing import Annotated, Literal

from bson import ObjectId
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator


def object_id(value: str) -> str:
    if not ObjectId.is_valid(value):
        raise ValueError("Expected a MongoDB ObjectId")
    return str(ObjectId(value))


SeedID = Annotated[str, AfterValidator(object_id)]


class SeedUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: SeedID
    srn: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role: Literal["student", "mentor", "admin"]
    email: str | None = None
    team_id: SeedID | None = None
    mentor_team_ids: list[SeedID] = Field(default_factory=list)
    created_at: datetime | None = None

    @field_validator("srn")
    @classmethod
    def normalize_srn(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("SRN cannot be blank")
        return value


class SeedTeam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: SeedID
    team_name: str = Field(min_length=1)
    mentor_id: SeedID | Literal[""]
    members: list[str] = Field(default_factory=list)
    created_at: datetime | None = None

    @field_validator("members")
    @classmethod
    def unique_members(cls, value: list[str]) -> list[str]:
        value = [member.strip().upper() for member in value]
        if any(not member for member in value):
            raise ValueError("Team members must have a nonblank SRN")
        if len(value) != len(set(value)):
            raise ValueError("A team cannot contain duplicate members")
        return value


class SeedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    users: list[SeedUser] = Field(default_factory=list)
    teams: list[SeedTeam] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_records(self):
        for label, values in (
            ("user IDs", [user.id for user in self.users]),
            ("SRNs", [user.srn for user in self.users]),
            ("team IDs", [team.id for team in self.teams]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {label} in seed data")
        memberships: dict[str, str] = {}
        for team in self.teams:
            for member in team.members:
                if member in memberships:
                    raise ValueError("A student cannot belong to multiple teams")
                memberships[member] = team.id
        for user in self.users:
            if (
                user.srn in memberships
                and "team_id" in user.model_fields_set
                and user.team_id != memberships[user.srn]
            ):
                raise ValueError("User team_id must match the team's member list")
        return self
