"""Find where resolved map places are named inside free transcript text.

Matches each place's canonical name and aliases as whole words, ignoring
case. A leading article is optional ("the Old Mill" also matches "Old
Mill"). When names overlap, the longest match wins, so "Silver Lake Inn"
is not also read as "Silver Lake".
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.map_location import MapLocation

_LEADING_ARTICLE = re.compile(r'^(?:the|a|an)\s+', re.IGNORECASE)


@dataclass(frozen=True)
class PlaceMention:
    """One place named in a piece of text.

    Attributes:
        location_id: Id of the resolved place that was named.
        start: Character offset where the name starts.
        end: Character offset just after the name.
    """

    location_id: str
    start: int
    end: int


def _name_variants(location: MapLocation) -> list[str]:
    """Return every spelling a place can be named by, without duplicates."""
    variants: list[str] = []
    for name in [location.canonical_name, *location.aliases]:
        cleaned = ' '.join(name.split())
        for variant in (cleaned, _LEADING_ARTICLE.sub('', cleaned)):
            if variant and variant.casefold() not in {item.casefold() for item in variants}:
                variants.append(variant)
    return variants


def _name_pattern(name: str) -> re.Pattern[str]:
    """Compile a whole-word, case-insensitive pattern for a place name."""
    words = [re.escape(word) for word in name.split()]
    return re.compile(r'(?<!\w)' + r'\s+'.join(words) + r'(?!\w)', re.IGNORECASE)


def find_place_mentions(text: str, locations: Sequence[MapLocation]) -> list[PlaceMention]:
    """Find every resolved place named in a piece of text.

    Args:
        text: Free text, such as one transcript segment.
        locations: Resolved places for the session.

    Returns:
        Non-overlapping mentions in the order they appear in the text.
    """
    candidates: list[PlaceMention] = []
    for location in locations:
        for name in _name_variants(location):
            for match in _name_pattern(name).finditer(text):
                candidates.append(PlaceMention(location.id, match.start(), match.end()))

    # Longest names claim their text first; shorter overlapping ones are dropped.
    candidates.sort(key=lambda item: (-(item.end - item.start), item.start))
    mentions: list[PlaceMention] = []
    for candidate in candidates:
        if any(candidate.start < kept.end and kept.start < candidate.end for kept in mentions):
            continue
        mentions.append(candidate)
    return sorted(mentions, key=lambda item: item.start)


def location_is_mentioned(text: str, location: MapLocation) -> bool:
    """Return whether a single place is named anywhere in the text."""
    return any(_name_pattern(name).search(text) for name in _name_variants(location))
