"""Read spoken spatial relationships between places from the transcript.

Looks for sentences where one place is described relative to another,
for example "Oakwood lies just north of Silver Lake", "the cellar inside
the Keep" or "Raven Peak, near the Shadow Cave". Each match becomes a
typed MapEdge (near, inside, north_of or east_of) pointing from the place
being described to the place it is described against.

Only the words between two consecutive place names are inspected, and
they must be a short linking phrase ending in the relation ("is", "lies
just", "which sits far" ...). This keeps sentences like "we left Phandalin
and camped in Silver Lake" from being read as Phandalin inside Silver Lake.
Reversed phrasings ("north of the lake lies Oakwood") are not detected;
the DM can tag those by hand.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from itertools import pairwise
from typing import Any

from app.domain.map_edge import MapEdge, MapEdgeRelationship, canonical_connection
from app.domain.map_location import MapLocation
from app.domain.transcript_store import TranscriptSegment
from app.functions.geo.place_mentions import find_place_mentions

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?;])\s+')

# Words allowed between the described place and the relation itself.
_LINK = (
    r'(?:,\s*)?'
    r'(?:(?:which|that|it)\s+)?'
    r'(?:(?:is|are|was|were|lies|lay|sits|sat|stands|stood|located|situated|built|hidden|'
    r'nestled|found)\s+)*'
    r'(?:(?:just|right|directly|due|far|further|farther|somewhere|a\s+little|a\s+bit|'
    r"a\s+short\s+way|a\s+few\s+miles|a\s+day's\s+(?:walk|ride))\s+)*"
)
_ARTICLE = r'(?:\s+(?:the|a|an))?'

# (gap pattern, relationship name); None means read the compass direction.
_RELATIONS: list[tuple[re.Pattern[str], str | None]] = [
    (
        re.compile(
            r'^' + _LINK + r'(?P<direction>north|south|east|west)(?:ward)?\s+of' + _ARTICLE + '$'
        ),
        None,
    ),
    (
        re.compile(
            r'^' + _LINK + r'(?:inside|within|in\s+the\s+(?:heart|middle|center|centre)\s+of|'
            r'deep\s+(?:in|inside|within)|in)' + _ARTICLE + '$'
        ),
        'inside',
    ),
    (
        re.compile(
            r'^'
            + _LINK
            + r'(?:near|nearby|next\s+to|beside|close\s+to|not\s+far\s+from)'
            + _ARTICLE
            + '$'
        ),
        'near',
    ),
]


def relation_between(gap: str) -> str | None:
    """Return the relationship named by the words between two places, if any.

    Args:
        gap: Text between the end of the first place name and the start of
            the second one.

    Returns:
        A relationship name ('north_of', 'south_of', 'inside', 'near', ...)
        or None when the gap is not a recognised linking phrase.
    """
    text = ' '.join(gap.casefold().split())
    for pattern, relationship in _RELATIONS:
        match = pattern.match(text)
        if match is None:
            continue
        direction = match.groupdict().get('direction')
        return f'{direction}_of' if direction else relationship
    return None


def _event_ids_by_time(events: Sequence[Any]) -> dict[float, list[str]]:
    """Index timeline events by the transcript start time they were extracted from."""
    index: dict[float, list[str]] = {}
    for event in events:
        event_id = str(getattr(event, 'id', '') or '')
        if event_id:
            index.setdefault(float(getattr(event, 'timestamp', 0.0) or 0.0), []).append(event_id)
    return index


def extract_spatial_edges(
    locations: Sequence[MapLocation],
    segments: Sequence[TranscriptSegment],
    events: Sequence[Any] = (),
    session_id: str = 'default',
    first_index: int = 0,
) -> list[MapEdge]:
    """Turn spatial relationships spoken in the transcript into typed edges.

    Repeated statements of the same relationship collapse onto one edge;
    each statement's segment start time is kept as evidence, together with
    the timeline events extracted from that segment.

    Args:
        locations: Resolved places for the session.
        segments: The session's transcript segments.
        events: The session's timeline events, used to link evidence.
        session_id: Session the edges belong to.
        first_index: Number of edges already on the map, so new edge ids
            and ``order`` continue after them.

    Returns:
        New typed MapEdges in the order they were first spoken.
    """
    if len(locations) < 2:
        return []

    events_at = _event_ids_by_time(events)
    edges: list[MapEdge] = []
    by_key: dict[tuple[str, str, MapEdgeRelationship], MapEdge] = {}

    for segment in segments:
        for sentence in _SENTENCE_SPLIT.split(segment.text):
            mentions = find_place_mentions(sentence, locations)
            for first, second in pairwise(mentions):
                if first.location_id == second.location_id:
                    continue
                relationship = relation_between(sentence[first.end : second.start])
                if relationship is None:
                    continue
                key = canonical_connection(first.location_id, second.location_id, relationship)
                edge = by_key.get(key)
                if edge is None:
                    from_id, to_id, kind = key
                    edge = MapEdge(
                        id=f'edge_{first_index + len(edges) + 1}',
                        session_id=session_id,
                        from_location_id=from_id,
                        to_location_id=to_id,
                        relationship=kind,
                        order=first_index + len(edges),
                    )
                    by_key[key] = edge
                    edges.append(edge)
                if segment.start not in edge.evidence_times:
                    edge.evidence_times.append(segment.start)
                for event_id in events_at.get(segment.start, []):
                    if event_id not in edge.evidence_event_ids:
                        edge.evidence_event_ids.append(event_id)
    return edges
