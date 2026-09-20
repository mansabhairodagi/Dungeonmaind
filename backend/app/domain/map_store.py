"""Async-safe in-memory store for a session's resolved map graph."""

import asyncio

from app.domain.map_edge import MapEdge
from app.domain.map_location import MapLocation


class MapStore:
    """Async-safe in-memory store for map locations and edges, per session.

    Holds the output of the /map/generate orchestrator: the resolved
    MapLocations and inferred MapEdges for a session, saved together so
    GET /map can return both in one call.

    Attributes:
        _locations: Dict mapping session ID to its resolved MapLocations.
        _edges: Dict mapping session ID to its inferred MapEdges.
        _lock: Async lock for thread-safe access.
    """

    def __init__(self) -> None:
        self._locations: dict[str, list[MapLocation]] = {}
        self._edges: dict[str, list[MapEdge]] = {}
        self._lock = asyncio.Lock()

    async def save_map(
        self, session_id: str, locations: list[MapLocation], edges: list[MapEdge]
    ) -> None:
        """Save a session's resolved locations and inferred edges together.

        Args:
            session_id: The session identifier.
            locations: Resolved MapLocations for the session.
            edges: Inferred MapEdges for the session.
        """
        async with self._lock:
            self._locations[session_id] = list(locations)
            self._edges[session_id] = list(edges)

    async def get_locations(self, session_id: str) -> list[MapLocation] | None:
        """Get the saved locations for a session.

        Args:
            session_id: The session identifier.

        Returns:
            A copy of the saved MapLocations, or None if no map has been
            generated yet for this session.
        """
        async with self._lock:
            stored = self._locations.get(session_id)
            return list(stored) if stored is not None else None

    async def get_edges(self, session_id: str) -> list[MapEdge] | None:
        """Get the saved edges for a session.

        Args:
            session_id: The session identifier.

        Returns:
            A copy of the saved MapEdges, or None if no map has been
            generated yet for this session.
        """
        async with self._lock:
            stored = self._edges.get(session_id)
            return list(stored) if stored is not None else None

    async def has_map(self, session_id: str) -> bool:
        """Return whether a map has been generated for this session.

        Args:
            session_id: The session identifier.

        Returns:
            True if a map has been saved for this session.
        """
        async with self._lock:
            return session_id in self._locations

    async def clear_session(self, session_id: str) -> bool:
        """Clear a session's saved map.

        Args:
            session_id: The session identifier.

        Returns:
            True if a map existed and was removed, False otherwise.
        """
        async with self._lock:
            existed = session_id in self._locations or session_id in self._edges
            self._locations.pop(session_id, None)
            self._edges.pop(session_id, None)
            return existed


map_store = MapStore()
