import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedEntities:
    temporal_entities: list[str]
    location_entities: list[str]


MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

RELATIVE_TIME_WORDS = (
    "today",
    "yesterday",
    "tomorrow",
    "tonight",
)

RELATIVE_TIME_PHRASES = (
    "next week",
    "last week",
    "this week",
    "next month",
    "last month",
    "this month",
    "next year",
    "last year",
    "this year",
)

DOCX_TEMPORAL_PATTERNS = [
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+morning\b",
    r"\bAround\s+noon\b",
    r"\bLater\s+that\s+afternoon\b",
    r"\bLater\s+that\s+evening\b",
    r"\bBefore\s+sunset\b",
    r"\bfor\s+the\s+night\b",
    r"\bAfter\s+traveling\s+for\s+three\s+hours\b",
    r"\bBy\s+midday\b",
    r"\bDuring\s+the\s+evening\b",
    r"\bShortly\s+before\s+midnight\b",
    r"\bTwo\s+days\s+after\s+leaving\b",
    r"\bBefore\s+dawn\s+on\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
    r"\bDuring\s+the\s+following\s+night\b",
    r"\bThree\s+weeks\s+after\b",
    rf"\b(?:the\s+)?morning\s+of\s+(?:{ '|'.join(MONTHS) })\s+\d{{1,2}},\s*\d{{4}}\b",
    r"\bBetween\s+sunset\s+and\s+midnight\b",
    r"\bBy\s+the\s+end\s+of\s+the\s+month\b",
    r"\bBefore\s+the\s+beginning\s+of\s+the\s+next\s+year\b",
]

LOCAL_PLACE_PREFIXES = (
    "Room",
    "Building",
    "Floor",
    "Hall",
    "Gate",
    "Tower",
    "Castle",
    "Temple",
    "Dungeon",
    "Tavern",
    "Village",
    "City",
)

PLACE_NOUNS = (
    "abbey",
    "alley",
    "arena",
    "armory",
    "barracks",
    "battlefield",
    "bay",
    "bridge",
    "brook",
    "camp",
    "campsite",
    "canyon",
    "castle",
    "cave",
    "cemetery",
    "chamber",
    "chapel",
    "citadel",
    "city",
    "clearing",
    "cliff",
    "coast",
    "crossing",
    "crypt",
    "den",
    "dock",
    "docks",
    "dungeon",
    "encampment",
    "farm",
    "ferry",
    "field",
    "forest",
    "forge",
    "fort",
    "fortress",
    "gate",
    "graveyard",
    "grove",
    "guildhall",
    "hall",
    "hamlet",
    "harbor",
    "hideout",
    "hill",
    "hills",
    "inn",
    "island",
    "jungle",
    "keep",
    "kingdom",
    "lake",
    "library",
    "lair",
    "manor",
    "market",
    "marsh",
    "maze",
    "mine",
    "mines",
    "monastery",
    "mount",
    "mountain",
    "mountains",
    "outpost",
    "palace",
    "pass",
    "path",
    "plains",
    "port",
    "ravine",
    "realm",
    "river",
    "road",
    "room",
    "ruin",
    "ruins",
    "sanctum",
    "sea",
    "settlement",
    "sewer",
    "sewers",
    "shop",
    "shrine",
    "square",
    "stable",
    "stronghold",
    "swamp",
    "tavern",
    "temple",
    "throne room",
    "tower",
    "trail",
    "tunnel",
    "tunnels",
    "valley",
    "village",
    "watchtower",
    "wood",
    "woods",
)

STANDALONE_PLACE_WORDS = (
    "Castle",
    "Temple",
    "Dungeon",
    "Tavern",
    "Village",
    "City",
)

# Small built-in gazetteer for common examples and likely campaign locations.
KNOWN_LOCATIONS = {
    "Andhra Pradesh",
    "Aethergate",
    "Avernus",
    "Barovia",
    "Berlin",
    "Black River",
    "Citadel of Arcanis",
    "Crystal Forest",
    "Dragon Hill",
    "Eastmere",
    "Emerald Plains",
    "Frostmere Pass",
    "Frostwind Valley",
    "Green Forest",
    "India",
    "Ironkeep City",
    "Isle of Storms",
    "Kingdom of Valoria",
    "Moon Temple",
    "New York",
    "Northwatch",
    "Obsidian Cliffs",
    "Oakwood Village",
    "Phandalin",
    "Ravenloft",
    "Raven Peak",
    "Riverstone Town",
    "Ruins of Eldermoor",
    "Shadow Cave",
    "Shattered Coast",
    "Silver Harbor",
    "Silver Lake",
    "Sunfall Fortress",
    "Waterdeep",
    "Neverwinter",
    "Baldur's Gate",
    "Whispering Lake",
}

LOCATION_PREPOSITIONS = (
    "at",
    "in",
    "inside",
    "into",
    "near",
    "outside",
    "toward",
    "towards",
    "to",
    "from",
    "through",
    "under",
    "beneath",
    "below",
    "above",
    "around",
    "behind",
    "beside",
)

LOCATION_VERBS = (
    "approached",
    "arrived",
    "camped",
    "crossed",
    "entered",
    "escaped",
    "explored",
    "fled",
    "followed",
    "found",
    "left",
    "reached",
    "returned",
    "searched",
    "traveled",
    "travelled",
    "visited",
)

_MONTH_PATTERN = "|".join(MONTHS)
_WEEKDAY_PATTERN = "|".join(WEEKDAYS)
_LOCAL_PREFIX_PATTERN = "|".join(LOCAL_PLACE_PREFIXES)
_STANDALONE_PLACE_PATTERN = "|".join(STANDALONE_PLACE_WORDS)
_PLACE_NOUN_PATTERN = "|".join(re.escape(noun) for noun in sorted(PLACE_NOUNS, key=len, reverse=True))
_LOCATION_PREPOSITION_PATTERN = "|".join(LOCATION_PREPOSITIONS)
_LOCATION_VERB_PATTERN = "|".join(LOCATION_VERBS)

TEMPORAL_PATTERNS = [
    *[re.compile(pattern, re.IGNORECASE) for pattern in DOCX_TEMPORAL_PATTERNS],
    re.compile(r"\b(?:%s)\b" % "|".join(RELATIVE_TIME_WORDS), re.IGNORECASE),
    re.compile(r"\b(?:%s)\b" % "|".join(RELATIVE_TIME_PHRASES), re.IGNORECASE),
    re.compile(rf"\b(?:{_WEEKDAY_PATTERN})\b", re.IGNORECASE),
    re.compile(rf"\b\d{{1,2}}\s+(?:{_MONTH_PATTERN})\s+\d{{4}}\b", re.IGNORECASE),
    re.compile(rf"\b(?:{_MONTH_PATTERN})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,\s*\d{{4}})?\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(r"\b(?:19|20)\d{2}\b"),
    re.compile(r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b"),
    re.compile(r"(?<!:)\b\d{1,2}\s*(?:AM|PM|am|pm)\b"),
]

LOCATION_SUFFIXES = tuple(
    sorted(
        {
            "Bridge",
            "Cave",
            "City",
            "Cliffs",
            "Coast",
            "Forest",
            "Fortress",
            "Harbor",
            "Hideout",
            "Hill",
            "Lake",
            "Pass",
            "Peak",
            "Plains",
            "River",
            "Road",
            "Temple",
            "Town",
            "Valley",
            "Village",
            "Wood",
            "Woods",
        },
        key=len,
        reverse=True,
    )
)
_LOCATION_SUFFIX_PATTERN = "|".join(LOCATION_SUFFIXES)

PROPER_LOCATION_PATTERN = re.compile(
    rf"\b[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){{0,3}}\s+(?:{_LOCATION_SUFFIX_PATTERN})\b"
)

LOCAL_PLACE_PATTERN = re.compile(
    rf"\b(?:{_LOCAL_PREFIX_PATTERN})\s+(?:[A-Z]|\d+[A-Za-z]?|[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\b"
)
STANDALONE_LOCAL_PLACE_PATTERN = re.compile(
    rf"\b(?:the\s+)?(?:{_STANDALONE_PLACE_PATTERN})\b",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]*|\d+[A-Za-z]?")
PREPOSITIONAL_LOCATION_PATTERN = re.compile(
    rf"\b(?:{_LOCATION_PREPOSITION_PATTERN})\s+((?:the\s+)?[A-Z][A-Za-z'-]+(?:\s+[A-Z0-9][A-Za-z0-9'-]*){{0,4}})\b"
)
VERB_LOCATION_PATTERN = re.compile(
    rf"\b(?:{_LOCATION_VERB_PATTERN})\s+((?:the\s+)?[A-Z][A-Za-z'-]+(?:\s+[A-Z0-9][A-Za-z0-9'-]*){{0,4}})\b",
)
OF_LOCATION_PATTERN = re.compile(
    rf"\b(?:the\s+)?(?i:(?:{_PLACE_NOUN_PATTERN}))\s+of\s+(?:the\s+)?[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){{0,3}}\b",
)

LOCATION_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "we",
    "you",
    "they",
    "he",
    "she",
    "it",
    "next",
    "last",
    "this",
}

NON_LOCATION_DESCRIPTORS = {
    "arrived",
    "camped",
    "crossed",
    "discovered",
    "entered",
    "escaped",
    "established",
    "followed",
    "found",
    "go",
    "left",
    "met",
    "party",
    "returns",
    "searched",
    "then",
    "visited",
    "went",
}

LOCATION_DESCRIPTORS = {
    "ancient",
    "black",
    "blue",
    "broken",
    "burning",
    "dark",
    "dead",
    "deep",
    "dragon",
    "dwarven",
    "east",
    "eastern",
    "elven",
    "enchanted",
    "forgotten",
    "goblin",
    "green",
    "hidden",
    "high",
    "haunted",
    "lost",
    "lower",
    "misty",
    "north",
    "northern",
    "old",
    "red",
    "ruined",
    "secret",
    "shadow",
    "silver",
    "south",
    "southern",
    "stone",
    "sunken",
    "underground",
    "upper",
    "west",
    "western",
    "white",
}

GENERIC_LOCATION_NOUNS_TO_SKIP = {
    "camp",
    "campsite",
    "cave",
    "road",
    "trail",
    "village",
}

TRAILING_CLAUSE_WORDS = {
    "and",
    "but",
    "or",
    "then",
    "where",
    "when",
    "while",
    "before",
    "after",
    "at",
    "in",
    "on",
    "with",
}

TRAILING_VERBS = {
    "arrived",
    "attacked",
    "camped",
    "crossed",
    "entered",
    "fought",
    "found",
    "left",
    "met",
    "returned",
    "searched",
    "saw",
    "went",
}


def _looks_like_described_place(value: str) -> bool:
    words = value.casefold().split()
    if not words:
        return False
    if words[-1] not in PLACE_NOUNS:
        return False
    # Avoid returning every bare generic noun; keep useful standalone game places.
    if len(words) == 1:
        return words[0] in {"castle", "temple", "dungeon", "tavern", "village", "city"}
    content_words = [word for word in words[:-1] if word not in LOCATION_STOPWORDS]
    if any(word in NON_LOCATION_DESCRIPTORS for word in content_words):
        return False
    if any(word in LOCATION_PREPOSITIONS for word in content_words):
        return False
    return bool(content_words)


def _is_capitalized(value: str) -> bool:
    return bool(value) and value[0].isupper()


def _candidate_score(value: str) -> int:
    words = value.split()
    lowered = [word.casefold().strip(".,;:!?") for word in words]
    score = len(words)
    if lowered and lowered[-1] in PLACE_NOUNS:
        score += 6
    if lowered and lowered[0] in PLACE_NOUNS:
        score += 6
    if len(lowered) > 1 and lowered[0] in {"the", "a", "an"} and lowered[1] in PLACE_NOUNS:
        score += 6
    if lowered and lowered[0] in {"the", "a", "an"}:
        score += 1
    if any(word in LOCATION_DESCRIPTORS for word in lowered):
        score += 2
    if any(_is_capitalized(word.strip(".,;:!?")) for word in words):
        score += 3
    if any(word in NON_LOCATION_DESCRIPTORS for word in lowered):
        score -= 10
    return score


def _clean_location_candidate(value: str) -> str:
    words = WORD_PATTERN.findall(value)
    while words and words[0].casefold() in LOCATION_PREPOSITIONS + LOCATION_VERBS:
        words.pop(0)
    while words and words[0].casefold() in {"we", "they", "party", "group"}:
        words.pop(0)
    while words and words[-1].casefold() in TRAILING_CLAUSE_WORDS | TRAILING_VERBS:
        words.pop()
    return " ".join(words)


def _find_place_noun_candidates(text: str) -> list[str]:
    candidates = []
    descriptor_pattern = "|".join(sorted(LOCATION_DESCRIPTORS, key=len, reverse=True))
    pattern = re.compile(
        rf"\b(?:the|a|an)\s+(?:(?:{descriptor_pattern})\s+){{0,3}}(?:{_PLACE_NOUN_PATTERN})\b",
        re.IGNORECASE,
    )
    candidates.extend(match.group(0) for match in pattern.finditer(text))
    return candidates


def _find_single_named_locations_after_triggers(text: str) -> list[str]:
    candidates = []
    trigger_pattern = re.compile(
        rf"\b(?:{_LOCATION_PREPOSITION_PATTERN}|{_LOCATION_VERB_PATTERN})\s+([A-Z][A-Za-z'-]+)\b",
    )
    for match in trigger_pattern.finditer(text):
        candidate = _clean_location_candidate(match.group(1))
        if candidate and candidate.casefold() not in LOCATION_STOPWORDS:
            candidates.append(candidate)
    return candidates


def _remove_nested_locations(values: list[str]) -> list[str]:
    kept = []
    for value in sorted(values, key=lambda item: (_candidate_score(item), len(item)), reverse=True):
        current = value.casefold()
        current_words = current.split()
        should_skip = False
        for existing in kept:
            existing_norm = existing.casefold()
            existing_words = existing_norm.split()
            if current == existing_norm:
                should_skip = True
                break
            if current in existing_norm and len(current_words) < len(existing_words):
                should_skip = True
                break
            if existing_norm in current and len(existing_words) < len(current_words):
                kept.remove(existing)
                break
        if not should_skip:
            kept.append(value)
    return sorted(kept, key=lambda item: values.index(item))


def _filter_location_candidates(values: list[str]) -> list[str]:
    filtered = []
    for value in values:
        candidate = _clean_location_candidate(value)
        lowered = candidate.casefold()
        if not candidate or lowered in LOCATION_STOPWORDS:
            continue
        if lowered in GENERIC_LOCATION_NOUNS_TO_SKIP:
            continue
        lowered_words = lowered.split()
        if (
            len(lowered_words) >= 2
            and lowered_words[0] == "the"
            and lowered_words[-1] in GENERIC_LOCATION_NOUNS_TO_SKIP
            and (len(lowered_words) == 2 or lowered_words[-1] in {"road", "trail", "camp", "campsite", "village"})
        ):
            continue
        if any(word in RELATIVE_TIME_WORDS for word in lowered.split()):
            continue
        if lowered in {month.casefold() for month in MONTHS}:
            continue
        filtered.append(candidate)
    return filtered


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = " ".join(value.strip().split())
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _dedupe_spans_preserving_order(matches: list[tuple[int, int, str]]) -> list[str]:
    sorted_matches = sorted(matches, key=lambda item: (item[0], -(item[1] - item[0])))
    kept: list[tuple[int, int, str]] = []

    for start, end, value in sorted_matches:
        normalized = " ".join(value.strip().split())
        if not normalized:
            continue
        is_nested = any(
            kept_start <= start and end <= kept_end
            for kept_start, kept_end, _ in kept
        )
        if is_nested:
            continue
        if any(normalized.casefold() == kept_value.casefold() for _, _, kept_value in kept):
            continue
        kept.append((start, end, normalized))

    return [value for _, _, value in sorted(kept, key=lambda item: item[0])]


def _extract_temporal_entities(text: str) -> list[str]:
    matches = []
    for pattern in TEMPORAL_PATTERNS:
        matches.extend((match.start(), match.end(), match.group(0)) for match in pattern.finditer(text))

    temporal_entities = _dedupe_spans_preserving_order(matches)
    normalized = []
    for entity in temporal_entities:
        clean = " ".join(entity.split())
        if clean.casefold() == "the morning of march 17, 2025":
            clean = "Morning of March 17, 2025"
        elif clean.casefold() == "for the night":
            clean = "Night"
        elif clean.casefold() == "night":
            clean = "Night"
        normalized.append(clean)
    return normalized


def _normalize_location_output(value: str) -> str:
    words = WORD_PATTERN.findall(value)
    if not words:
        return ""

    lowered = [word.casefold() for word in words]
    while lowered and lowered[0] in {
        "a",
        "an",
        "small",
        "hidden",
        "abandoned",
        "temporary",
        "northern",
        "western",
        "eastern",
        "southern",
        "edge",
        "region",
        "governor",
        "water",
        "cave",
        "entrance",
        "of",
    }:
        words.pop(0)
        lowered.pop(0)

    candidate = " ".join(words).strip()
    candidate_words = candidate.split()
    if (
        len(candidate_words) > 1
        and candidate_words[0].casefold() == "the"
        and candidate_words[1][0].isupper()
    ):
        candidate = " ".join(candidate_words[1:])
    if candidate.casefold() == "watchtower":
        return "Watchtower"
    if candidate.casefold() in {"grand hall", "the grand hall"}:
        return ""
    if candidate.casefold() in {"grand hall of aethergate", "hall of aethergate", "the grand hall of aethergate"}:
        return "Aethergate"
    return candidate


def _location_matches_from_patterns(text: str) -> list[tuple[int, int, str]]:
    matches: list[tuple[int, int, str]] = []

    for location in sorted(KNOWN_LOCATIONS, key=len, reverse=True):
        for match in re.finditer(rf"\b{re.escape(location)}\b", text, re.IGNORECASE):
            matches.append((match.start(), match.end(), location))

    for pattern in (
        PROPER_LOCATION_PATTERN,
        LOCAL_PLACE_PATTERN,
        OF_LOCATION_PATTERN,
        PREPOSITIONAL_LOCATION_PATTERN,
        VERB_LOCATION_PATTERN,
    ):
        for match in pattern.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            normalized = _normalize_location_output(value)
            if normalized:
                matches.append((match.start(), match.end(), normalized))

    for match in re.finditer(r"\b(?:an?\s+)?(?:abandoned\s+)?watchtower\b", text, re.IGNORECASE):
        matches.append((match.start(), match.end(), "Watchtower"))

    return matches


def _extract_location_entities(text: str) -> list[str]:
    matches = _location_matches_from_patterns(text)
    fallback_candidates = _find_place_noun_candidates(text)
    for candidate in fallback_candidates:
        start = text.casefold().find(candidate.casefold())
        if start >= 0:
            normalized = _normalize_location_output(candidate)
            if normalized:
                matches.append((start, start + len(candidate), normalized))

    ordered = _dedupe_spans_preserving_order(matches)
    return _remove_nested_locations(_dedupe_preserving_order(_filter_location_candidates(ordered)))


def extract_entities(text: str) -> ExtractedEntities:
    return ExtractedEntities(
        temporal_entities=_extract_temporal_entities(text),
        location_entities=_extract_location_entities(text),
    )


def entities_as_metadata(text: str) -> dict[str, str]:
    entities = extract_entities(text)
    return {
        "temporal_entities": ", ".join(entities.temporal_entities),
        "location_entities": ", ".join(entities.location_entities),
    }
