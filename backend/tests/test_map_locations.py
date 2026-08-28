import unittest

from app.api.routers.map import list_locations
from app.domain.models import TimelineEvent
from app.domain.timeline_store import timeline_store


def _event(
    event_id: str, places: list[str], order: int, session_id: str = 'sess-1'
) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        session_id=session_id,
        title=event_id,
        description='',
        order=order,
        location_entities=places,
    )


class MapLocationsApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await timeline_store.clear_all()

    async def asyncTearDown(self) -> None:
        await timeline_store.clear_all()

    async def test_get_map_locations_returns_resolved_places_for_session(self) -> None:
        await timeline_store.add_events(
            [
                _event('evt_1', ['Velmora Crossing'], order=1),
                _event('evt_2', ['Silver Lake'], order=2),
                _event('evt_3', ['Ye Olde Tavern'], order=3),
                _event('evt_4', ['the tavern'], order=4),
            ]
        )

        payload = await list_locations(session_id='sess-1')

        self.assertEqual(payload.session_id, 'sess-1')
        self.assertEqual(payload.total, 3)
        self.assertEqual([location.id for location in payload.locations], ['loc_1', 'loc_2', 'loc_3'])
        self.assertEqual(payload.locations[0].canonical_name, 'Velmora Crossing')
        self.assertEqual(payload.locations[1].canonical_name, 'Silver Lake')
        self.assertEqual(payload.locations[2].canonical_name, 'Ye Olde Tavern')
        self.assertEqual(payload.locations[2].aliases, ['the tavern'])
        self.assertEqual(payload.locations[2].event_ids, ['evt_3', 'evt_4'])

    async def test_get_map_locations_defaults_to_empty_session(self) -> None:
        payload = await list_locations(session_id='default')

        self.assertEqual(payload.session_id, 'default')
        self.assertEqual(payload.locations, [])
        self.assertEqual(payload.total, 0)


if __name__ == '__main__':
    unittest.main()
