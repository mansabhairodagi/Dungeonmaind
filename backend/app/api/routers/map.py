"""REST API router for session map locations.

Until MapStore exists, locations are resolved on each request from the
in-memory timeline event list.
"""

from fastapi import APIRouter, Query

from app.api.mappers.map_mapper import map_location_to_out
from app.base_models.map_base_models import MapLocationListResponse
from app.domain.timeline_store import timeline_store
from app.functions.geo.place_resolver import resolve_locations

router = APIRouter()


@router.get('/locations', response_model=MapLocationListResponse)
async def list_locations(
    session_id: str = Query('default', description='Session identifier'),
) -> MapLocationListResponse:
    """List resolved map places for a session.

    Normalizes, dedupes, and alias-merges location_entities from the
    session's ordered timeline events. Backed by the in-memory timeline
    store until a dedicated MapStore exists.

    Args:
        session_id: Session identifier (default 'default').

    Returns:
        MapLocationListResponse with one MapLocationOut per resolved place.
    """
    events = await timeline_store.get_session_events(session_id)
    locations = resolve_locations(events, session_id=session_id)
    return MapLocationListResponse(
        session_id=session_id,
        locations=[map_location_to_out(location) for location in locations],
        total=len(locations),
    )
