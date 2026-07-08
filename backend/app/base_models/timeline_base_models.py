from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TimelineEventOut(BaseModel):
    id: str
    session_id: str
    title: str
    description: str
    event_type: str
    order: int
    timestamp: float = 0.0
    transcription_chunk_id: Optional[str] = None
    player_id: Optional[str] = None
    speaker_name: Optional[str] = None
    temporal_entities: list[str] = Field(default_factory=list)
    location_entities: list[str] = Field(default_factory=list)
    created_at: datetime


class TimelineEventListResponse(BaseModel):
    session_id: str
    events: list[TimelineEventOut]
    total: int


class TimelineGenerateRequest(BaseModel):
    session_id: str = "default"


class TimelineGenerateResponse(BaseModel):
    session_id: str
    events_generated: int
    events: list[TimelineEventOut]


class TimelineDeleteResponse(BaseModel):
    deleted: bool
    event_id: Optional[str] = None
