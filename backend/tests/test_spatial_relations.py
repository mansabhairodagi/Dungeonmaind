import tempfile
import unittest
from unittest import mock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers.map import router as map_router
from app.core.config import settings
from app.domain.map_edge import MapEdgeRelationship
from app.domain.map_location import MapLocation
from app.domain.map_store import map_store
from app.domain.models import TimelineEvent
from app.domain.timeline_store import timeline_store
from app.domain.transcript_store import TranscriptSegment, transcript_store
from app.functions.geo.build_map import generate_map
from app.functions.geo.place_mentions import find_place_mentions
from app.functions.geo.spatial_relations import extract_spatial_edges, relation_between

SESSION_ID = 'sess-spatial'


def _location(location_id: str, name: str, aliases: list[str] | None = None) -> MapLocation:
    return MapLocation(
        id=location_id, session_id=SESSION_ID, canonical_name=name, aliases=aliases or []
    )


def _segment(start: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=start + 4.0, text=text, speaker='DM')


LOCATIONS = [
    _location('loc_1', 'Oakwood Village', aliases=['Oakwood']),
    _location('loc_2', 'Silver Lake'),
    _location('loc_3', 'The Keep'),
    _location('loc_4', 'Cellar'),
    _location('loc_5', 'Silver Lake Inn'),
]


def _relations(text: str, start: float = 0.0) -> list[tuple[str, str, MapEdgeRelationship]]:
    edges = extract_spatial_edges(LOCATIONS, [_segment(start, text)], session_id=SESSION_ID)
    return [(edge.from_location_id, edge.to_location_id, edge.relationship) for edge in edges]


class RelationPhraseTests(unittest.TestCase):
    def test_linking_phrases_are_recognised(self) -> None:
        self.assertEqual(relation_between(' lies just north of '), 'north_of')
        self.assertEqual(relation_between(' is inside the '), 'inside')
        self.assertEqual(relation_between(' in the heart of '), 'inside')
        self.assertEqual(relation_between(', near the '), 'near')
        self.assertEqual(relation_between(" is a day's walk west of "), 'west_of')

    def test_other_words_between_places_are_not_relations(self) -> None:
        self.assertIsNone(relation_between(' and camped in '))
        self.assertIsNone(relation_between(' before we reached '))
        self.assertIsNone(relation_between(', which sits far to the '))
        self.assertIsNone(relation_between(' to '))


class PlaceMentionTests(unittest.TestCase):
    def test_longest_name_wins_and_aliases_match(self) -> None:
        mentions = find_place_mentions('From Oakwood we rowed to the Silver Lake Inn.', LOCATIONS)
        self.assertEqual([item.location_id for item in mentions], ['loc_1', 'loc_5'])

    def test_names_match_whole_words_only(self) -> None:
        self.assertEqual(find_place_mentions('The Keepers of Cellarbrook', LOCATIONS), [])


class ExtractSpatialEdgesTests(unittest.TestCase):
    def test_north_of(self) -> None:
        self.assertEqual(
            _relations('Oakwood lies just north of Silver Lake.'),
            [('loc_1', 'loc_2', MapEdgeRelationship.north_of)],
        )

    def test_south_of_is_stored_as_reversed_north_of(self) -> None:
        self.assertEqual(
            _relations('Silver Lake is south of Oakwood Village.'),
            [('loc_1', 'loc_2', MapEdgeRelationship.north_of)],
        )

    def test_west_of_is_stored_as_reversed_east_of(self) -> None:
        self.assertEqual(
            _relations('The Keep stands west of Silver Lake.'),
            [('loc_2', 'loc_3', MapEdgeRelationship.east_of)],
        )

    def test_inside(self) -> None:
        self.assertEqual(
            _relations('We searched the cellar inside the Keep.'),
            [('loc_4', 'loc_3', MapEdgeRelationship.inside)],
        )

    def test_near(self) -> None:
        self.assertEqual(
            _relations('The Silver Lake Inn, near Oakwood, was quiet.'),
            [('loc_5', 'loc_1', MapEdgeRelationship.near)],
        )

    def test_travel_sentence_is_not_a_spatial_relation(self) -> None:
        self.assertEqual(_relations('We left Oakwood and camped in Silver Lake.'), [])

    def test_relation_does_not_cross_sentences(self) -> None:
        self.assertEqual(_relations('We reached Oakwood. North of Silver Lake we rested.'), [])

    def test_repeated_statements_collapse_and_keep_every_time(self) -> None:
        segments = [
            _segment(12.0, 'Oakwood is north of Silver Lake.'),
            _segment(80.5, 'Remember, Oakwood lies north of Silver Lake.'),
        ]
        events = [
            TimelineEvent(
                id='evt_7', session_id=SESSION_ID, title='t', description='d', timestamp=80.5
            )
        ]
        edges = extract_spatial_edges(LOCATIONS, segments, events, SESSION_ID, first_index=3)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].evidence_times, [12.0, 80.5])
        self.assertEqual(edges[0].evidence_event_ids, ['evt_7'])
        self.assertEqual((edges[0].id, edges[0].order), ('edge_4', 3))


class GenerateMapWithSpatialEdgesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._patch = mock.patch.object(settings, 'backend_root_path', self._tmp.name)
        self._patch.start()
        await timeline_store.clear_all()
        await transcript_store.clear_session(SESSION_ID)
        await map_store.clear_session(SESSION_ID)
        await timeline_store.add_events(
            [
                TimelineEvent(
                    id='evt_1',
                    session_id=SESSION_ID,
                    title='Arrive',
                    description='',
                    order=1,
                    timestamp=3.0,
                    location_entities=['Oakwood Village'],
                ),
                TimelineEvent(
                    id='evt_2',
                    session_id=SESSION_ID,
                    title='Lake',
                    description='',
                    order=2,
                    timestamp=9.0,
                    location_entities=['Silver Lake'],
                ),
            ]
        )
        await transcript_store.add_segments(
            SESSION_ID,
            [
                _segment(3.0, 'We arrive in Oakwood Village.'),
                _segment(9.0, 'Oakwood Village lies north of Silver Lake.'),
            ],
        )

    async def asyncTearDown(self) -> None:
        await timeline_store.clear_all()
        await transcript_store.clear_session(SESSION_ID)
        await map_store.clear_session(SESSION_ID)
        self._patch.stop()
        self._tmp.cleanup()

    async def test_generate_stores_typed_edge_from_transcript(self) -> None:
        _, edges = await generate_map(SESSION_ID)
        typed = [edge for edge in edges if edge.relationship == MapEdgeRelationship.north_of]
        self.assertEqual(len(typed), 1)
        self.assertEqual(typed[0].evidence_times, [9.0])
        self.assertEqual(typed[0].evidence_event_ids, ['evt_2'])
        self.assertEqual([edge.id for edge in edges], [f'edge_{i + 1}' for i in range(len(edges))])

    async def test_edges_endpoint_returns_typed_edge_without_generate(self) -> None:
        app = FastAPI()
        app.include_router(map_router, prefix='/map')
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/map/edges', params={'session_id': SESSION_ID})
        self.assertEqual(response.status_code, 200)
        typed = [edge for edge in response.json()['edges'] if edge['relationship'] == 'north_of']
        self.assertEqual(len(typed), 1)
        self.assertEqual(typed[0]['evidence_times'], [9.0])


if __name__ == '__main__':
    unittest.main()
