"""Orchestrates place resolution and link inference into one saved map.

Glues together the place resolver and the link builder: fetch a session's
ordered timeline events, resolve them into places, infer the links between
those places, and persist both into the shared MapStore. This is the
/map/generate entry point — no new matching or inference logic lives here.
"""

from __future__ import annotations

from app.domain.map_edge import MapEdge
from app.domain.map_location import MapLocation
from app.domain.map_store import map_store
from app.domain.timeline_store import timeline_store
from app.functions.geo.link_builder import build_edges
from app.functions.geo.place_resolver import resolve_locations


async def generate_map(session_id: str) -> tuple[list[MapLocation], list[MapEdge]]:
    """Resolve, link, and persist the map for one session.

    Args:
        session_id: The session identifier.

    Returns:
        A tuple of (resolved MapLocations, inferred MapEdges) for the
        session, in the same order they were saved to the MapStore.
    """
    events = await timeline_store.get_session_events(session_id)
    locations = resolve_locations(events, session_id=session_id)
    edges = build_edges(locations, events, session_id=session_id)
    await map_store.save_map(session_id, locations, edges)
    return locations, edges
