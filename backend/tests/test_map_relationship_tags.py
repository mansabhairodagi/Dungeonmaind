import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers.map import router as map_router
from app.core.config import settings
from app.domain.map_store import map_store
from app.domain.models import Group, Role, TimelineEvent
from app.domain.store import store
from app.domain.timeline_store import timeline_store
from app.domain.transcript_store import TranscriptSegment, transcript_store
from app.functions.geo.build_map import generate_map

SESSION_ID = 'sess-tags'


def _event(event_id: str, place: str, order: int) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        session_id=SESSION_ID,
        title=event_id,
        description='',
        order=order,
        timestamp=float(order),
        location_entities=[place],
    )


class MapRelationshipTagTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        patch = mock.patch.object(settings, 'backend_root_path', self._tmp.name)
        patch.start()
        self.addCleanup(patch.stop)

        self._original_group = store.group
        store.group = Group()
        self.leader = store.group.add_player('Ana', Role.leader)
        self.member = store.group.add_player('Ben', Role.member)

        await timeline_store.clear_all()
        await transcript_store.clear_session(SESSION_ID)
        await map_store.clear_session(SESSION_ID)
        await timeline_store.add_events(
            [_event('evt_1', 'The Keep', 1), _event('evt_2', 'Cellar', 2)]
        )
        await transcript_store.add_segments(
            SESSION_ID,
            [
                TranscriptSegment(start=1.0, end=4.0, text='We ride up to the Keep.'),
                TranscriptSegment(start=2.0, end=6.0, text='Down the stairs is a cellar.'),
            ],
        )
        app = FastAPI()
        app.include_router(map_router, prefix='/map')
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        store.group = self._original_group
        await timeline_store.clear_all()
        await transcript_store.clear_session(SESSION_ID)
        await map_store.clear_session(SESSION_ID)

    def _tag(self, relationship: str, from_id='loc_2', to_id='loc_1', **extra) -> dict:
        return {
            'session_id': SESSION_ID,
            'from_location_id': from_id,
            'to_location_id': to_id,
            'relationship': relationship,
            **extra,
        }

    def _as(self, player) -> dict:
        return {'X-Player-Id': str(player.id)}

    def _overrides(self) -> dict:
        path = Path(self._tmp.name) / 'data' / 'map_overrides.json'
        return json.loads(path.read_text(encoding='utf-8'))['sessions'][SESSION_ID]

    async def test_transcript_lines_list_the_places_they_name(self) -> None:
        response = await self.client.get('/map/transcript', params={'session_id': SESSION_ID})

        self.assertEqual(response.status_code, 200)
        lines = response.json()['lines']
        self.assertEqual([line['location_ids'] for line in lines], [['loc_1'], ['loc_2']])
        self.assertEqual(lines[1]['start'], 2.0)

    async def test_leader_tag_is_saved_in_overrides_with_its_line(self) -> None:
        response = await self.client.post(
            '/map/relationships',
            json=self._tag('inside', segment_start=2.0),
            headers=self._as(self.leader),
        )

        self.assertEqual(response.status_code, 200)
        inside = [edge for edge in response.json()['edges'] if edge['relationship'] == 'inside']
        self.assertEqual(len(inside), 1)
        self.assertEqual(
            (inside[0]['from_location_id'], inside[0]['to_location_id']), ('loc_2', 'loc_1')
        )
        self.assertEqual(inside[0]['evidence_times'], [2.0])
        self.assertEqual(
            self._overrides()['connections']['added'],
            [
                {
                    'from_location_id': 'loc_2',
                    'to_location_id': 'loc_1',
                    'relationship': 'inside',
                    'segment_start': 2.0,
                }
            ],
        )

    async def test_tag_survives_regenerate(self) -> None:
        await self.client.post(
            '/map/relationships', json=self._tag('south_of'), headers=self._as(self.leader)
        )

        _, edges = await generate_map(SESSION_ID)

        self.assertIn(
            ('loc_1', 'loc_2', 'north_of'),
            [(edge.from_location_id, edge.to_location_id, edge.relationship) for edge in edges],
        )

    async def test_members_and_anonymous_callers_cannot_tag(self) -> None:
        member = await self.client.post(
            '/map/relationships', json=self._tag('near'), headers=self._as(self.member)
        )
        anonymous = await self.client.post('/map/relationships', json=self._tag('near'))

        self.assertEqual(member.status_code, 403)
        self.assertEqual(anonymous.status_code, 403)

    async def test_invalid_tags_are_rejected(self) -> None:
        headers = self._as(self.leader)
        travel = await self.client.post(
            '/map/relationships', json=self._tag('travel'), headers=headers
        )
        itself = await self.client.post(
            '/map/relationships', json=self._tag('near', to_id='loc_2'), headers=headers
        )
        unknown = await self.client.post(
            '/map/relationships', json=self._tag('near', to_id='loc_9'), headers=headers
        )

        self.assertEqual(travel.status_code, 422)
        self.assertEqual(itself.status_code, 422)
        self.assertEqual(unknown.status_code, 404)

    async def test_leader_can_remove_a_tag(self) -> None:
        headers = self._as(self.leader)
        await self.client.post('/map/relationships', json=self._tag('near'), headers=headers)

        response = await self.client.request(
            'DELETE', '/map/relationships', json=self._tag('near'), headers=headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('near', [edge['relationship'] for edge in response.json()['edges']])


if __name__ == '__main__':
    unittest.main()
