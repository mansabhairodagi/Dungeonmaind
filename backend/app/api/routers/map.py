"""REST API router for session map locations.

Until MapStore exists, locations are resolved on each request from the
in-memory timeline event list.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.mappers.map_mapper import map_edge_to_out, map_location_to_out
from app.api.mappers.timeline_mapper import timeline_event_to_out
from app.base_models.map_base_models import (
    MapEdgeListResponse,
    MapLocationListResponse,
    MapLocationOut,
)
from app.base_models.timeline_base_models import TimelineEventListResponse
from app.domain.map_edge import MapEdge
from app.domain.map_location import MapLocation
from app.domain.models import TimelineEvent
from app.domain.timeline_store import timeline_store
from app.functions.geo.link_builder import build_edges
from app.functions.geo.place_resolver import resolve_locations

router = APIRouter()


async def _session_events_and_locations(
    session_id: str,
) -> tuple[list[TimelineEvent], list[MapLocation]]:
    """Resolve map locations from the session's in-memory timeline events."""
    events = await timeline_store.get_session_events(session_id)
    return events, resolve_locations(events, session_id=session_id)


async def _session_edges(session_id: str) -> tuple[list[MapLocation], list[MapEdge]]:
    """Resolve locations then infer their edges for a session.

    Backed by the in-memory timeline store until a dedicated MapStore
    exists: both places and links are recomputed on each request.
    """
    events, locations = await _session_events_and_locations(session_id)
    return locations, build_edges(locations, events, session_id=session_id)


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
    _, locations = await _session_events_and_locations(session_id)
    return MapLocationListResponse(
        session_id=session_id,
        locations=[map_location_to_out(location) for location in locations],
        total=len(locations),
    )


@router.get('/locations/{location_id}/events', response_model=TimelineEventListResponse)
async def list_location_events(
    location_id: str, session_id: str = Query('default', description='Session identifier')
) -> TimelineEventListResponse:
    """List timeline events linked to a resolved map place.

    Reads event_ids already stored on the MapLocation and fetches those
    TimelineEvents. Does not re-scan location names.

    Args:
        location_id: Resolved place id (loc_1, loc_2, ...).
        session_id: Session identifier (default 'default').

    Returns:
        TimelineEventListResponse for the linked events.

    Raises:
        HTTPException 404: If the location is not found in the session.
    """
    events, locations = await _session_events_and_locations(session_id)
    location = next((item for item in locations if item.id == location_id), None)
    if location is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Location not found')

    events_by_id = {event.id: event for event in events}
    linked = [events_by_id[event_id] for event_id in location.event_ids if event_id in events_by_id]
    return TimelineEventListResponse(
        session_id=session_id,
        events=[timeline_event_to_out(event) for event in linked],
        total=len(linked),
    )


@router.get('/events/{event_id}/location', response_model=MapLocationOut)
async def get_event_location(
    event_id: str, session_id: str = Query('default', description='Session identifier')
) -> MapLocationOut:
    """Find the resolved map place linked to a timeline event.

    Reverse of GET /locations/{location_id}/events: scans resolved
    locations for the first whose event_ids contains this event.

    Args:
        event_id: Timeline event id (evt_4, ...).
        session_id: Session identifier (default 'default').

    Returns:
        MapLocationOut for the matching place.

    Raises:
        HTTPException 404: If no location lists this event.
    """
    _, locations = await _session_events_and_locations(session_id)
    location = next((item for item in locations if event_id in item.event_ids), None)
    if location is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Location not found')
    return map_location_to_out(location)


@router.get('/events/{event_id}/locations', response_model=MapLocationListResponse)
async def list_event_locations(
    event_id: str, session_id: str = Query('default', description='Session identifier')
) -> MapLocationListResponse:
    """List resolved map places linked to a timeline event.

    Reverse of GET /locations/{location_id}/events: returns every location
    whose event_ids contains this event.

    Args:
        event_id: Timeline event id (evt_4, ...).
        session_id: Session identifier (default 'default').

    Returns:
        MapLocationListResponse with the matching places.

    Raises:
        HTTPException 404: If no location lists this event.
    """
    _, locations = await _session_events_and_locations(session_id)
    matched = [item for item in locations if event_id in item.event_ids]
    if not matched:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Location not found')
    return MapLocationListResponse(
        session_id=session_id,
        locations=[map_location_to_out(item) for item in matched],
        total=len(matched),
    )


@router.get('/edges', response_model=MapEdgeListResponse)
async def list_edges(
    session_id: str = Query('default', description='Session identifier'),
) -> MapEdgeListResponse:
    """List inferred spatial links for a session.

    Resolves the session's places, then infers the travel and proximity
    edges between them from the ordered timeline. Backed by the in-memory
    timeline store until a dedicated MapStore exists.

    Args:
        session_id: Session identifier (default 'default').

    Returns:
        MapEdgeListResponse with one MapEdgeOut per inferred link.
    """
    _, edges = await _session_edges(session_id)
    return MapEdgeListResponse(
        session_id=session_id, edges=[map_edge_to_out(edge) for edge in edges], total=len(edges)
    )


@router.get('/locations/{location_id}/edges', response_model=MapEdgeListResponse)
async def list_location_edges(
    location_id: str, session_id: str = Query('default', description='Session identifier')
) -> MapEdgeListResponse:
    """List the inferred links that touch one resolved place.

    Returns every edge whose source or destination is this location, so the
    frontend can highlight the connections into and out of a single pin.

    Args:
        location_id: Resolved place id (loc_1, loc_2, ...).
        session_id: Session identifier (default 'default').

    Returns:
        MapEdgeListResponse with the edges touching this location (possibly
        empty if the place has no inferred links).

    Raises:
        HTTPException 404: If the location is not found in the session.
    """
    locations, edges = await _session_edges(session_id)
    if not any(item.id == location_id for item in locations):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='Location not found')

    touching = [
        edge for edge in edges if location_id in (edge.from_location_id, edge.to_location_id)
    ]
    return MapEdgeListResponse(
        session_id=session_id,
        edges=[map_edge_to_out(edge) for edge in touching],
        total=len(touching),
    )
