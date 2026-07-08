from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Use the domain enums as the single source of truth
from app.domain.models import PlayerStatus, Role


# Input models
class PlayerIn(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    role: Role
    reuse_id: UUID | None = None  # used for re-join / reuse flow


# Abilities
class Abilities(BaseModel):
    # "int_" kept to match frontend & domain model
    str: int
    dex: int
    con: int
    int_: int
    wis: int
    cha: int


class AbilitiesIn(BaseModel):
    str: int | None = None
    dex: int | None = None
    con: int | None = None
    int_: int | None = None
    wis: int | None = None
    cha: int | None = None


# HP (nested)
class Hp(BaseModel):
    current: int = 0
    max: int = 10
    temp: int = 0


class HpPatch(BaseModel):
    current: int | None = Field(None, ge=0)
    max: int | None = Field(None, ge=1)
    temp: int | None = Field(None, ge=0)


class MaxHpUpdate(BaseModel):
    max: int = Field(..., ge=1)


# Output models
class PlayerOut(BaseModel):
    id: UUID
    name: str
    role: Role
    status: PlayerStatus
    hp: Hp = Field(default_factory=Hp)
    created_at: datetime
    last_seen_at: datetime
    abilities: Abilities | None = None
    backend_url: str | None = None
    has_voiceprint: bool = False


# Optional: unified patch model (not currently used by routes)
class PlayerPatch(BaseModel):
    name: str | None = None
    role: Role | None = None

    hp: HpPatch | None = None
    abilities: AbilitiesIn | None = None

    # flat ability fields
    str: int | None = None
    dex: int | None = None
    con: int | None = None
    int_: int | None = None
    wis: int | None = None
    cha: int | None = None


# Action bodies
class PlayerDamageBody(BaseModel):
    damage: int = Field(..., ge=0)


class PlayerHealBody(BaseModel):
    heal: int = Field(..., ge=0)


# Group state
class GroupStateOut(BaseModel):
    group_id: UUID
    size: int
    max_size: int


# For /players/join/check
class JoinCheckOut(BaseModel):
    status: Literal['available', 'inactive_match', 'active_conflict']
    candidate: PlayerOut | None = None
