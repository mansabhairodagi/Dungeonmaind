"""Normalize and deduplicate place names from timeline location entities.

Part 1 uses a conservative substring / near-match heuristic only — no LLM
and no place-type dictionary. A short name collapses into a longer one only
when that longer name is the unique match among names actually seen.
If a short name could belong to more than one distinct place, it is left
unmerged (safe degradation).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.map_location import MapLocation

# Grammar only — not a place-type gazetteer. Dropped so 'the tavern' matches 'tavern'.
_MATCH_STOPWORDS = frozenset({'the', 'a', 'an', 'of'})


def normalize_place_name(value: str) -> str:
    """Normalize whitespace in a place name string.

    Args:
        value: Raw place name from location_entities.

    Returns:
        Place name with leading/trailing whitespace removed and internal
        whitespace collapsed to single spaces.
    """
    return ' '.join(value.strip().split())


def _matching_tokens(name: str) -> list[str]:
    """Tokenize a place name for heuristic comparison.

    Hyphens become spaces. Articles and 'of' are dropped so 'the tavern'
    and 'village of Phandalin' compare on content words only.
    """
    collapsed = normalize_place_name(name).casefold().replace('-', ' ')
    return [token for token in collapsed.split() if token and token not in _MATCH_STOPWORDS]


def _is_contiguous_subsequence(shorter: list[str], longer: list[str]) -> bool:
    """Return True if shorter tokens appear contiguously inside longer tokens."""
    if not shorter or not longer or len(shorter) > len(longer):
        return False
    span = len(shorter)
    for index in range(len(longer) - span + 1):
        if longer[index : index + span] == shorter:
            return True
    return False


def _edit_distance(left: str, right: str) -> int:
    """Levenshtein distance for short single-token near-matches."""
    if left == right:
        return 0
    previous = list(range(len(right) + 1))
    for i, left_ch in enumerate(left, start=1):
        current = [i]
        for j, right_ch in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (left_ch != right_ch)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _is_near_duplicate(left: str, right: str) -> bool:
    """Return True if two display names likely refer to the same place.

    Rules, in order:
    - Identical content tokens after stopword stripping.
    - Shorter token phrase is a whole-word contiguous substring of the longer.
    - Single tokens of length >= 5 differ by at most one edit (typo).
    """
    left_tokens = _matching_tokens(left)
    right_tokens = _matching_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    if left_tokens == right_tokens:
        return True
    if _is_contiguous_subsequence(left_tokens, right_tokens):
        return True
    if _is_contiguous_subsequence(right_tokens, left_tokens):
        return True
    if (
        len(left_tokens) == 1
        and len(right_tokens) == 1
        and min(len(left_tokens[0]), len(right_tokens[0])) >= 5
        and _edit_distance(left_tokens[0], right_tokens[0]) <= 1
    ):
        return True
    return False


def _specificity(name: str) -> tuple[int, int]:
    """Higher tuple means a more specific display name."""
    return (len(_matching_tokens(name)), len(normalize_place_name(name)))


def _is_more_specific(left: str, right: str) -> bool:
    """Return True if left is a more specific name than right."""
    return _specificity(left) > _specificity(right)


def _pick_canonical(names: list[str]) -> str:
    """Choose the most specific display name; ties keep the first-seen form."""
    best_index = 0
    best_score = _specificity(names[0])
    for index, name in enumerate(names[1:], start=1):
        score = _specificity(name)
        if score > best_score:
            best_score = score
            best_index = index
    return names[best_index]


class _UnionFind:
    """Disjoint-set keyed by casefolded place names."""

    def __init__(self, keys: list[str]) -> None:
        self._parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        parent = self._parent[key]
        if parent != key:
            parent = self.find(parent)
            self._parent[key] = parent
        return parent

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self._parent[right_root] = left_root


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    """Remove duplicate strings while preserving original order.

    Comparison is case-insensitive; the first occurrence's casing is kept.

    Args:
        values: List of normalized place name strings.

    Returns:
        Deduplicated list preserving first occurrence order.
    """
    seen = set()
    result = []
    for value in values:
        normalized = normalize_place_name(value)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _cluster_place_names(names: list[str]) -> list[list[str]]:
    """Group near-duplicate display names from this session only.

    Matching is uniqueness among the given names, not a static word list.
    Uncertain names stay separate.
    """
    unique = _dedupe_preserving_order(names)
    if not unique:
        return []

    keys = [name.casefold() for name in unique]
    union_find = _UnionFind(keys)

    by_signature: dict[tuple[str, ...], list[str]] = {}
    for name in unique:
        signature = tuple(_matching_tokens(name))
        if not signature:
            continue
        by_signature.setdefault(signature, []).append(name.casefold())
    for group in by_signature.values():
        for key in group[1:]:
            union_find.union(group[0], key)

    # Merge only when a shorter name uniquely matches one more-specific
    # cluster among names actually seen. Repeat so 'the tavern' can attach
    # after 'Olde Tavern' has already folded into 'Ye Olde Tavern'.
    changed = True
    while changed:
        changed = False
        for name in unique:
            name_root = union_find.find(name.casefold())
            candidate_roots: list[str] = []
            for other in unique:
                if other.casefold() == name.casefold():
                    continue
                if not _is_near_duplicate(name, other):
                    continue
                if not _is_more_specific(other, name):
                    continue
                root = union_find.find(other.casefold())
                if root == name_root:
                    continue
                if root not in candidate_roots:
                    candidate_roots.append(root)
            if len(candidate_roots) == 1:
                union_find.union(name.casefold(), candidate_roots[0])
                changed = True

    clustered: dict[str, list[str]] = {}
    for name in unique:
        clustered.setdefault(union_find.find(name.casefold()), []).append(name)

    ordered: list[list[str]] = []
    seen_roots: set[str] = set()
    for name in unique:
        root = union_find.find(name.casefold())
        if root in seen_roots:
            continue
        seen_roots.add(root)
        ordered.append(clustered[root])
    return ordered


def resolve_location_entities(location_entities: list[str]) -> list[str]:
    """Normalize, exact-dedupe, and merge near-duplicate place names.

    Args:
        location_entities: Raw location entity strings from one or more events.

    Returns:
        Canonical place names in first-seen cluster order.
    """
    clusters = _cluster_place_names(location_entities)
    return [_pick_canonical(cluster) for cluster in clusters]


def resolve_locations(
    events: Sequence[Any], session_id: str | None = None
) -> list[MapLocation]:
    """Resolve an ordered session timeline into one MapLocation per place.

    Wires together place-name normalization, exact-match dedupe, and
    alias-merge. Each location carries an ``event_ids`` index of every
    timeline event that mentioned it (canonical name or alias), so later
    lookup endpoints can read that list instead of scanning events again.
    ``first_order`` is the 0-based index of the first mentioning event
    in that ordered list.

    Args:
        events: Ordered TimelineEvent list for one session (order is used
            if the list is not already sorted).
        session_id: Optional session id override. Defaults to the first
            event's session_id, then 'default'.

    Returns:
        One MapLocation per resolved place, in first-seen cluster order.
    """
    ordered = sorted(events, key=lambda event: int(getattr(event, 'order', 0) or 0))
    resolved_session = session_id
    names_in_order: list[str] = []

    for event in ordered:
        if resolved_session is None:
            event_session = getattr(event, 'session_id', None)
            if event_session:
                resolved_session = str(event_session)
        for raw in getattr(event, 'location_entities', None) or []:
            name = normalize_place_name(str(raw))
            if name:
                names_in_order.append(name)

    if not names_in_order:
        return []

    resolved_session = resolved_session or 'default'
    clusters = _cluster_place_names(names_in_order)
    name_to_index: dict[str, int] = {}
    locations: list[MapLocation] = []

    for index, cluster in enumerate(clusters):
        canonical = _pick_canonical(cluster)
        aliases = [name for name in cluster if name.casefold() != canonical.casefold()]
        for name in cluster:
            name_to_index[name.casefold()] = index
        locations.append(
            MapLocation(
                id=f'loc_{index + 1}',
                session_id=resolved_session,
                canonical_name=canonical,
                aliases=aliases,
            )
        )

    for first_order, event in enumerate(ordered):
        event_id = str(getattr(event, 'id', '') or '')
        credited: set[int] = set()
        for raw in getattr(event, 'location_entities', None) or []:
            name = normalize_place_name(str(raw))
            if not name:
                continue
            index = name_to_index.get(name.casefold())
            if index is None:
                continue
            location = locations[index]
            location.mention_count += 1
            if location.mention_count == 1:
                location.first_order = first_order
            if event_id and index not in credited:
                credited.add(index)
                location.event_ids.append(event_id)

    return locations


def resolve_map_locations(
    events: list[Any], session_id: str | None = None
) -> list[MapLocation]:
    """Backward-compatible alias for :func:`resolve_locations`."""
    return resolve_locations(events, session_id=session_id)
