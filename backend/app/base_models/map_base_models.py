"""Pydantic models for map location request/response schemas."""

from pydantic import BaseModel, Field


class MapLocationOut(BaseModel):
    """Response model for a single resolved map location.

    Attributes:
        id: Unique location identifier (loc_1, loc_2, ...).
        session_id: Session this location belongs to.
        canonical_name: Primary display name for the location.
        aliases: Alternative names that resolved to this location.
        event_ids: Timeline event IDs that mention this location.
        mention_count: Total mentions across events.
        first_order: 0-based index of the first mentioning event in the session.
    """

    id: str
    session_id: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    mention_count: int = 0
    first_order: int = 0


class MapLocationListResponse(BaseModel):
    """Response model for the list of resolved places in a session."""

    session_id: str
    locations: list[MapLocationOut]
    total: int
