import unittest
from types import SimpleNamespace

from app.domain.models import TimelineEvent
from app.functions.geo.place_resolver import (
    normalize_place_name,
    resolve_location_entities,
    resolve_locations,
    resolve_map_locations,
)


def _event(event_id: str, places: list[str], order: int, session_id: str = 'sess-1'):
    return SimpleNamespace(
        id=event_id,
        session_id=session_id,
        order=order,
        location_entities=places,
    )


class PlaceResolverTests(unittest.TestCase):
    def test_normalize_place_name_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_place_name('  Silver   Lake  '), 'Silver Lake')

    def test_resolve_location_entities_dedupes_case_insensitive(self) -> None:
        raw = ['  Silver Lake ', 'silver lake', 'Silver Lake', 'Berlin', ' berlin ']
        self.assertEqual(
            resolve_location_entities(raw),
            ['Silver Lake', 'Berlin'],
        )

    def test_resolve_location_entities_preserves_first_seen_order(self) -> None:
        raw = ['Berlin', 'Silver Lake', 'berlin', 'Oakwood Village']
        self.assertEqual(
            resolve_location_entities(raw),
            ['Berlin', 'Silver Lake', 'Oakwood Village'],
        )

    def test_resolve_location_entities_skips_empty_values(self) -> None:
        self.assertEqual(resolve_location_entities(['', '   ', 'Berlin']), ['Berlin'])

    def test_resolve_location_entities_collapses_the_tavern_into_ye_olde_tavern(self) -> None:
        self.assertEqual(
            resolve_location_entities(['Ye Olde Tavern', 'the tavern']),
            ['Ye Olde Tavern'],
        )

    def test_resolve_location_entities_keeps_longer_name_when_short_name_comes_first(self) -> None:
        self.assertEqual(
            resolve_location_entities(['the tavern', 'Ye Olde Tavern']),
            ['Ye Olde Tavern'],
        )

    def test_resolve_location_entities_does_not_merge_ambiguous_short_names(self) -> None:
        self.assertEqual(
            resolve_location_entities(['Castle Black', 'White Castle', 'the castle']),
            ['Castle Black', 'White Castle', 'the castle'],
        )

    def test_resolve_location_entities_does_not_merge_inn_into_inner_sanctum(self) -> None:
        self.assertEqual(
            resolve_location_entities(['the inn', 'Inner Sanctum']),
            ['the inn', 'Inner Sanctum'],
        )

    def test_resolve_location_entities_merges_unlisted_place_names(self) -> None:
        self.assertEqual(
            resolve_location_entities(['Black Gloomhold', 'the gloomhold']),
            ['Black Gloomhold'],
        )

    def test_resolve_location_entities_does_not_merge_ambiguous_unlisted_names(self) -> None:
        self.assertEqual(
            resolve_location_entities(['Black Gloomhold', 'Red Gloomhold', 'the gloomhold']),
            ['Black Gloomhold', 'Red Gloomhold', 'the gloomhold'],
        )


class MapLocationResolverTests(unittest.TestCase):
    def test_evt3_and_evt4_resolve_to_one_map_location(self) -> None:
        events = [
            _event('evt_3', ['Ye Olde Tavern'], order=3),
            _event('evt_4', ['the tavern'], order=4),
        ]

        locations = resolve_locations(events)

        self.assertEqual(len(locations), 1)
        location = locations[0]
        self.assertEqual(location.canonical_name, 'Ye Olde Tavern')
        self.assertEqual(location.aliases, ['the tavern'])
        self.assertEqual(location.event_ids, ['evt_3', 'evt_4'])
        self.assertEqual(location.mention_count, 2)
        self.assertEqual(location.first_order, 3)
        self.assertEqual(location.session_id, 'sess-1')
        self.assertEqual(location.id, 'ye-olde-tavern')

    def test_unique_short_name_merges_into_the_only_matching_place(self) -> None:
        events = [
            _event('evt_1', ['Castle Ravenloft'], order=1),
            _event('evt_2', ['the castle'], order=2),
        ]

        locations = resolve_locations(events)

        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].canonical_name, 'Castle Ravenloft')
        self.assertEqual(locations[0].aliases, ['the castle'])
        self.assertEqual(locations[0].event_ids, ['evt_1', 'evt_2'])

    def test_ambiguous_short_name_degrades_safely(self) -> None:
        events = [
            _event('evt_1', ['Silver Lake'], order=1),
            _event('evt_2', ['Black Lake'], order=2),
            _event('evt_3', ['the lake'], order=3),
        ]

        locations = resolve_locations(events)
        names = [location.canonical_name for location in locations]

        self.assertEqual(names, ['Silver Lake', 'Black Lake', 'the lake'])
        self.assertEqual(locations[0].event_ids, ['evt_1'])
        self.assertEqual(locations[1].event_ids, ['evt_2'])
        self.assertEqual(locations[2].event_ids, ['evt_3'])

    def test_article_variant_is_exact_match_after_stripping(self) -> None:
        events = [
            _event('evt_1', ['The Silver Lake'], order=1),
            _event('evt_2', ['Silver Lake'], order=2),
        ]

        locations = resolve_locations(events)

        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].canonical_name, 'The Silver Lake')
        self.assertEqual(locations[0].aliases, ['Silver Lake'])
        self.assertEqual(locations[0].event_ids, ['evt_1', 'evt_2'])

    def test_resolve_locations_accepts_timeline_events_and_indexes_lookups(self) -> None:
        events = [
            TimelineEvent(
                id='evt_4',
                session_id='sess-1',
                title='Asked around',
                description='Rumors at the tavern.',
                order=4,
                location_entities=['the tavern'],
            ),
            TimelineEvent(
                id='evt_3',
                session_id='sess-1',
                title='Arrival',
                description='The party enters Ye Olde Tavern.',
                order=3,
                location_entities=['Ye Olde Tavern'],
            ),
        ]

        locations = resolve_locations(events)
        by_id = {location.id: location.event_ids for location in locations}

        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].first_order, 3)
        self.assertEqual(by_id['ye-olde-tavern'], ['evt_3', 'evt_4'])

    def test_resolve_locations_records_an_event_once_when_it_mentions_aliases(self) -> None:
        events = [_event('evt_3', ['Ye Olde Tavern', 'the tavern'], order=3)]

        locations = resolve_locations(events)

        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].event_ids, ['evt_3'])
        self.assertEqual(locations[0].mention_count, 2)

    def test_resolve_locations_returns_empty_for_events_without_places(self) -> None:
        self.assertEqual(resolve_locations([_event('evt_1', [], order=1)]), [])
        self.assertEqual(resolve_locations([]), [])

    def test_resolve_map_locations_is_an_alias_of_resolve_locations(self) -> None:
        events = [
            _event('evt_3', ['Ye Olde Tavern'], order=3),
            _event('evt_4', ['the tavern'], order=4),
        ]
        self.assertEqual(
            resolve_map_locations(events)[0].event_ids,
            resolve_locations(events)[0].event_ids,
        )


if __name__ == '__main__':
    unittest.main()
