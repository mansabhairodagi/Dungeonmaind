import tempfile
import unittest
from pathlib import Path

from app.domain.map_edge import (
    MapEdge,
    MapEdgeRelationship,
    canonical_connection,
    parse_relationship,
)
from app.domain.map_location import MapLocation
from app.domain.map_overrides import MapConnectionChange, SessionMapOverrides
from app.functions.geo.map_overrides import (
    apply_map_overrides,
    load_session_overrides,
    record_added_connection,
    record_removed_connection,
)


def _location(location_id: str, name: str) -> MapLocation:
    return MapLocation(id=location_id, session_id='sess-1', canonical_name=name)


def _edge(from_id: str, to_id: str, relationship: MapEdgeRelationship) -> MapEdge:
    return MapEdge(
        id='edge_1',
        session_id='sess-1',
        from_location_id=from_id,
        to_location_id=to_id,
        relationship=relationship,
    )


class ParseRelationshipTests(unittest.TestCase):
    def test_spoken_forms_map_to_stored_relationships(self) -> None:
        self.assertEqual(parse_relationship('North of'), (MapEdgeRelationship.north_of, False))
        self.assertEqual(parse_relationship('south-of'), (MapEdgeRelationship.north_of, True))
        self.assertEqual(parse_relationship('west_of'), (MapEdgeRelationship.east_of, True))
        self.assertEqual(parse_relationship('next to'), (MapEdgeRelationship.near, False))
        self.assertEqual(parse_relationship('within'), (MapEdgeRelationship.inside, False))
        self.assertIsNone(parse_relationship('above'))

    def test_south_and_west_are_stored_as_reversed_edges(self) -> None:
        self.assertEqual(
            canonical_connection('loc_1', 'loc_2', 'south_of'),
            ('loc_2', 'loc_1', MapEdgeRelationship.north_of),
        )
        self.assertEqual(
            canonical_connection('loc_1', 'loc_2', 'west of'),
            ('loc_2', 'loc_1', MapEdgeRelationship.east_of),
        )

    def test_unknown_relationship_falls_back_to_proximity(self) -> None:
        self.assertEqual(
            canonical_connection('loc_1', 'loc_2', 'linked'),
            ('loc_1', 'loc_2', MapEdgeRelationship.proximity),
        )

    def test_typed_edge_round_trips_through_dict(self) -> None:
        edge = _edge('loc_1', 'loc_2', MapEdgeRelationship.inside)
        self.assertEqual(MapEdge.from_dict(edge.to_dict()).relationship, MapEdgeRelationship.inside)


class TypedOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / 'map_overrides.json'
        self.locations = [_location('loc_1', 'Cellar'), _location('loc_2', 'Keep')]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_added_typed_connection_keeps_its_type(self) -> None:
        overrides = SessionMapOverrides(
            added_connections=[MapConnectionChange('loc_1', 'loc_2', 'inside')]
        )
        _, edges = apply_map_overrides(self.locations, [], overrides)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].relationship, MapEdgeRelationship.inside)

    def test_two_typed_links_on_one_pair_are_not_duplicates(self) -> None:
        record_added_connection('sess-1', 'loc_1', 'loc_2', 'inside', path=self.path)
        record_added_connection('sess-1', 'loc_1', 'loc_2', 'north_of', path=self.path)
        overrides = load_session_overrides('sess-1', self.path)
        self.assertEqual(
            [item.relationship for item in overrides.added_connections], ['inside', 'north_of']
        )

    def test_south_of_is_saved_reversed_and_applied(self) -> None:
        overrides = record_added_connection('sess-1', 'loc_1', 'loc_2', 'south of', path=self.path)
        saved = overrides.added_connections[0]
        self.assertEqual(
            (saved.from_location_id, saved.to_location_id, saved.relationship),
            ('loc_2', 'loc_1', 'north_of'),
        )
        _, edges = apply_map_overrides(self.locations, [], overrides)
        self.assertEqual(
            (edges[0].from_location_id, edges[0].to_location_id, edges[0].relationship),
            ('loc_2', 'loc_1', MapEdgeRelationship.north_of),
        )

    def test_removing_one_typed_link_keeps_the_other(self) -> None:
        edges = [
            _edge('loc_1', 'loc_2', MapEdgeRelationship.travel),
            _edge('loc_1', 'loc_2', MapEdgeRelationship.inside),
        ]
        overrides = record_removed_connection('sess-1', 'loc_1', 'loc_2', 'inside', path=self.path)
        _, kept = apply_map_overrides(self.locations, edges, overrides)
        self.assertEqual([edge.relationship for edge in kept], [MapEdgeRelationship.travel])

    def test_removing_west_of_matches_the_stored_east_of_edge(self) -> None:
        edges = [_edge('loc_2', 'loc_1', MapEdgeRelationship.east_of)]
        overrides = record_removed_connection('sess-1', 'loc_1', 'loc_2', 'west_of', path=self.path)
        _, kept = apply_map_overrides(self.locations, edges, overrides)
        self.assertEqual(kept, [])


if __name__ == '__main__':
    unittest.main()
