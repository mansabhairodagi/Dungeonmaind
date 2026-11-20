import tempfile
import unittest
from unittest import mock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers.map import router as map_router
from app.core.config import settings
from app.domain.map_store import map_store
from app.domain.models import TimelineEvent
from app.domain.timeline_store import timeline_store
from app.domain.transcript_store import TranscriptSegment, transcript_store
from app.functions.geo.map_overrides import record_rename

SESSION_ID = 'sess-mentions'


def _event(event_id: str, place: str, order: int, timestamp: float) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        session_id=SESSION_ID,
        title=f'Scene {order}',
        description='',
        order=order,
        timestamp=timestamp,
        location_entities=[place],
    )


class MapMentionsRouterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        patch = mock.patch.object(settings, 'backend_root_path', self._tmp.name)
        patch.start()
        self.addCleanup(patch.stop)
        await timeline_store.clear_all()
        await transcript_store.clear_session(SESSION_ID)
        await map_store.clear_session(SESSION_ID)
        await timeline_store.add_events(
            [_event('evt_1', 'Phandalin', 1, 12.0), _event('evt_2', 'Cragmaw Castle', 2, 47.5)]
        )
        app = FastAPI()
        app.include_router(map_router, prefix='/map')
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        await timeline_store.clear_all()
        await transcript_store.clear_session(SESSION_ID)
        await map_store.clear_session(SESSION_ID)

    async def _mentions(self, location_id: str) -> list[dict]:
        response = await self.client.get(
            f'/map/locations/{location_id}/mentions', params={'session_id': SESSION_ID}
        )
        self.assertEqual(response.status_code, 200)
        return response.json()['mentions']

    async def test_transcript_lines_naming_the_place_are_returned_in_order(self) -> None:
        await transcript_store.add_segments(
            SESSION_ID,
            [
                TranscriptSegment(start=12.0, end=15.0, text='We reach Phandalin.', speaker='DM'),
                TranscriptSegment(start=20.0, end=22.0, text='Pass the snacks.', speaker='Ben'),
                TranscriptSegment(start=90.0, end=93.0, text='Back to phandalin!', speaker='Ana'),
            ],
        )

        mentions = await self._mentions('loc_1')

        self.assertEqual([item['start'] for item in mentions], [12.0, 90.0])
        self.assertEqual(mentions[1]['speaker'], 'Ana')
        self.assertEqual({item['source'] for item in mentions}, {'transcript'})

    async def test_a_longer_place_name_is_not_a_mention_of_the_shorter_one(self) -> None:
        # Two longer names keep the resolver from folding 'Phandalin' into either one.
        await timeline_store.add_events(
            [_event('evt_3', 'Phandalin Inn', 3, 60.0), _event('evt_4', 'Phandalin Mine', 4, 80.0)]
        )
        await transcript_store.add_segments(
            SESSION_ID,
            [
                TranscriptSegment(start=60.0, end=62.0, text='We rest at the Phandalin Inn.'),
                TranscriptSegment(start=70.0, end=72.0, text='Phandalin is quiet tonight.'),
            ],
        )

        mentions = await self._mentions('loc_1')

        self.assertEqual([item['start'] for item in mentions], [70.0])

    async def test_old_spoken_name_still_matches_after_a_rename(self) -> None:
        await transcript_store.add_segments(
            SESSION_ID,
            [TranscriptSegment(start=47.0, end=50.0, text='Cragmaw Castle looms ahead.')],
        )
        record_rename(SESSION_ID, 'loc_2', 'The Goblin Fort')

        mentions = await self._mentions('loc_2')

        self.assertEqual([item['start'] for item in mentions], [47.0])

    async def test_falls_back_to_event_times_without_a_transcript(self) -> None:
        mentions = await self._mentions('loc_2')

        self.assertEqual(
            mentions,
            [
                {
                    'start': 47.5,
                    'end': 47.5,
                    'text': 'Scene 2',
                    'speaker': 'unknown',
                    'source': 'event',
                }
            ],
        )

    async def test_unknown_place_is_404(self) -> None:
        response = await self.client.get(
            '/map/locations/loc_99/mentions', params={'session_id': SESSION_ID}
        )
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
