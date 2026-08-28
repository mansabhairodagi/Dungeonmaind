import unittest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routers.map import router as map_router
from app.base_models.map_base_models import MapLocationListResponse, MapLocationOut
from app.base_models.timeline_base_models import TimelineEventListResponse, TimelineEventOut
from app.domain.models import TimelineEvent
from app.domain.timeline_store import timeline_store

SESSION_ID = 'sess-1'


def _event(event_id: str, places: list[str], order: int) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        session_id=SESSION_ID,
        title=event_id,
        description='',
        order=order,
        timestamp=float(order),
        location_entities=places,
    )


def _map_app() -> FastAPI:
    application = FastAPI()
    application.include_router(map_router, prefix='/map')
    return application


class MapLocationsRouterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await timeline_store.clear_all()
        await timeline_store.add_events(
            [
                _event('evt_1', ['Velmora Crossing'], order=1),
                _event('evt_2', ['Silver Lake'], order=2),
                _event('evt_3', ['Ye Olde Tavern'], order=3),
                _event('evt_4', ['the tavern'], order=4),
            ]
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=_map_app()),
            base_url='http://test',
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        await timeline_store.clear_all()

    async def test_get_map_locations_matches_worked_example_contract(self) -> None:
        response = await self.client.get(
            '/map/locations', params={'session_id': SESSION_ID}
        )

        self.assertEqual(response.status_code, 200)
        payload = MapLocationListResponse.model_validate(response.json())
        self.assertEqual(payload.session_id, SESSION_ID)
        self.assertEqual(payload.total, 3)
        self.assertEqual(len(payload.locations), 3)
        self.assertEqual(
            [location.id for location in payload.locations],
            ['loc_1', 'loc_2', 'loc_3'],
        )
        self.assertEqual(payload.locations[0].canonical_name, 'Velmora Crossing')
        self.assertEqual(payload.locations[1].canonical_name, 'Silver Lake')
        self.assertEqual(payload.locations[2].canonical_name, 'Ye Olde Tavern')
        self.assertEqual(payload.locations[2].aliases, ['the tavern'])
        self.assertEqual(payload.locations[2].event_ids, ['evt_3', 'evt_4'])
        self._assert_location_contract(payload.locations)

    async def test_get_location_events_matches_worked_example_contract(self) -> None:
        response = await self.client.get(
            '/map/locations/loc_3/events', params={'session_id': SESSION_ID}
        )

        self.assertEqual(response.status_code, 200)
        payload = TimelineEventListResponse.model_validate(response.json())
        self.assertEqual(payload.session_id, SESSION_ID)
        self.assertEqual(payload.total, 2)
        self.assertEqual(len(payload.events), 2)
        self.assertEqual([event.id for event in payload.events], ['evt_3', 'evt_4'])
        self.assertEqual(payload.events[0].location_entities, ['Ye Olde Tavern'])
        self.assertEqual(payload.events[1].location_entities, ['the tavern'])
        self._assert_event_contract(payload.events)

    async def test_get_event_locations_matches_worked_example_contract(self) -> None:
        response = await self.client.get(
            '/map/events/evt_4/locations', params={'session_id': SESSION_ID}
        )

        self.assertEqual(response.status_code, 200)
        payload = MapLocationListResponse.model_validate(response.json())
        self.assertEqual(payload.session_id, SESSION_ID)
        self.assertEqual(payload.total, 1)
        self.assertEqual(len(payload.locations), 1)
        self.assertEqual(payload.locations[0].id, 'loc_3')
        self.assertEqual(payload.locations[0].canonical_name, 'Ye Olde Tavern')
        self.assertEqual(payload.locations[0].aliases, ['the tavern'])
        self.assertEqual(payload.locations[0].event_ids, ['evt_3', 'evt_4'])
        self._assert_location_contract(payload.locations)

    def _assert_location_contract(self, locations: list[MapLocationOut]) -> None:
        for location in locations:
            self.assertTrue(location.id)
            self.assertEqual(location.session_id, SESSION_ID)
            self.assertTrue(location.canonical_name)
            self.assertIsInstance(location.aliases, list)
            self.assertIsInstance(location.event_ids, list)
            self.assertGreaterEqual(location.mention_count, 1)
            self.assertGreaterEqual(location.first_order, 1)

    def _assert_event_contract(self, events: list[TimelineEventOut]) -> None:
        for event in events:
            self.assertTrue(event.id)
            self.assertEqual(event.session_id, SESSION_ID)
            self.assertTrue(event.title)
            self.assertIsInstance(event.location_entities, list)
            self.assertIsInstance(event.timestamp, float)
            self.assertIsNotNone(event.created_at)


if __name__ == '__main__':
    unittest.main()
