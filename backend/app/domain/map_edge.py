"""Domain model for inferred spatial links between map locations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MapEdgeRelationship(StrEnum):
    """How two locations are spatially related on the schematic map.

    ``travel`` and ``proximity`` are inferred from the timeline. The rest
    are typed spatial relations read from what was said at the table.
    Directed relations read "from is <relation> to": an ``inside`` edge
    from A to B means A is inside B, a ``north_of`` edge means A is north
    of B. "south of" and "west of" are stored as the reversed
    ``north_of`` / ``east_of`` edge so the map only has two axes.
    """

    travel = 'travel'
    proximity = 'proximity'
    near = 'near'
    inside = 'inside'
    north_of = 'north_of'
    east_of = 'east_of'


# Spoken or hand-typed relationship names -> (stored relationship, reversed?).
_RELATIONSHIP_ALIASES: dict[str, tuple[MapEdgeRelationship, bool]] = {
    'travel': (MapEdgeRelationship.travel, False),
    'traveled': (MapEdgeRelationship.travel, False),
    'proximity': (MapEdgeRelationship.proximity, False),
    'near': (MapEdgeRelationship.near, False),
    'next_to': (MapEdgeRelationship.near, False),
    'beside': (MapEdgeRelationship.near, False),
    'close_to': (MapEdgeRelationship.near, False),
    'inside': (MapEdgeRelationship.inside, False),
    'within': (MapEdgeRelationship.inside, False),
    'in': (MapEdgeRelationship.inside, False),
    'north_of': (MapEdgeRelationship.north_of, False),
    'south_of': (MapEdgeRelationship.north_of, True),
    'east_of': (MapEdgeRelationship.east_of, False),
    'west_of': (MapEdgeRelationship.east_of, True),
}


def parse_relationship(value: str | None) -> tuple[MapEdgeRelationship, bool] | None:
    """Parse a relationship name into its stored form.

    Args:
        value: Relationship name such as ``"north of"``, ``"south_of"`` or
            ``"travel"``. Case, spaces and hyphens are ignored.

    Returns:
        ``(relationship, reversed)``, where ``reversed`` means the edge must
        point the other way (``south_of`` A->B is stored as ``north_of``
        B->A). None if the name is not recognised.
    """
    token = '_'.join((value or '').strip().lower().replace('-', ' ').split())
    return _RELATIONSHIP_ALIASES.get(token)


def canonical_connection(
    from_location_id: str, to_location_id: str, relationship: str | None
) -> tuple[str, str, MapEdgeRelationship]:
    """Return a connection in the direction and vocabulary edges are stored in.

    Unknown relationship names fall back to ``proximity``, matching how
    untyped links between two places have always been treated.

    Args:
        from_location_id: Source location id as given.
        to_location_id: Destination location id as given.
        relationship: Relationship name as given.

    Returns:
        ``(from_location_id, to_location_id, relationship)`` with "south of"
        and "west of" flipped onto ``north_of`` / ``east_of``.
    """
    parsed = parse_relationship(relationship)
    if parsed is None:
        return from_location_id, to_location_id, MapEdgeRelationship.proximity
    kind, flipped = parsed
    if flipped:
        return to_location_id, from_location_id, kind
    return from_location_id, to_location_id, kind


@dataclass
class MapEdge:
    """A directed link between two canonical locations in a session.

    Edges are inferred from the party's timeline, not from coordinates:
    a ``travel`` edge records that the party moved from one place to the
    next across consecutive events, while a ``proximity`` edge records
    that two places were mentioned together within a single event. Typed
    spatial edges (near, inside, north_of, east_of) come from relations
    spoken in the transcript or tagged by the DM.

    Attributes:
        id: Unique edge identifier (edge_1, edge_2, ...).
        session_id: Identifier for the session this edge belongs to.
        from_location_id: Source location id (loc_1, loc_2, ...).
        to_location_id: Destination location id.
        relationship: Kind of link (see MapEdgeRelationship).
        evidence_event_ids: Timeline event IDs that support this edge.
        order: 0-based position of the edge in the inferred journey.
        evidence_times: Start times (seconds) of the transcript segments the
            relationship was read from. Empty for timeline-inferred edges.
    """

    id: str
    session_id: str
    from_location_id: str
    to_location_id: str
    relationship: MapEdgeRelationship = field(default_factory=lambda: MapEdgeRelationship.travel)
    evidence_event_ids: list[str] = field(default_factory=list)
    order: int = 0
    evidence_times: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize this edge for timeline/map export.

        ``evidence_times`` is only written when present, so map.json files
        without spoken relationships keep their earlier shape.
        """
        relationship = self.relationship
        data = {
            'id': self.id,
            'session_id': self.session_id,
            'from_location_id': self.from_location_id,
            'to_location_id': self.to_location_id,
            'relationship': relationship.value
            if isinstance(relationship, MapEdgeRelationship)
            else str(relationship),
            'evidence_event_ids': list(self.evidence_event_ids),
            'order': self.order,
        }
        if self.evidence_times:
            data['evidence_times'] = list(self.evidence_times)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> MapEdge:
        """Deserialize an edge written by export."""
        return cls(
            id=data['id'],
            session_id=data['session_id'],
            from_location_id=data['from_location_id'],
            to_location_id=data['to_location_id'],
            relationship=MapEdgeRelationship(data.get('relationship', 'travel')),
            evidence_event_ids=list(data.get('evidence_event_ids', [])),
            order=int(data.get('order', 0)),
            evidence_times=[float(value) for value in data.get('evidence_times', [])],
        )
