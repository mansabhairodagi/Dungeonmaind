import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.domain.models import TimelineEvent, TimelineEventType
from app.functions.embedding.entity_extractor import (
    _dedupe_preserving_order,
    _extract_entities_with_local_llm,
)

EVENT_EXTRACTION_PROMPT = (
    'You are analyzing a Dungeons & Dragons session transcript. '
    'Identify the most significant events in the text below. '
    'An event is something meaningful that happens: a combat encounter, a discovery, '
    'an important dialogue with an NPC, a travel milestone, a quest started or completed, '
    'a rest period, or any other notable occurrence.\n\n'
    'Return a JSON array of objects. Each object must have these fields:\n'
    '- "title": a short, concise title (5-10 words)\n'
    '- "description": a 1-2 sentence description of what happened\n'
    '- "event_type": one of "combat", "discovery", "dialogue", "travel", "rest", "quest", "other"\n\n'
    'Rules:\n'
    '- Titles must be specific, not generic\n'
    '- Limit to the most important 3-5 events in the text\n'
    '- Do not include meta-discussion or out-of-character chatter\n'
    '- Return ONLY valid JSON, no other text\n'
)


def _safe_json_from_llm_response(content: str) -> list[dict[str, Any]]:
    content = content.strip()
    if not content:
        return []

    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            events = parsed.get('events') or parsed.get('results') or []
            return events if isinstance(events, list) else []
    except json.JSONDecodeError:
        pass

    start = content.find('[')
    end = content.rfind(']')
    if start < 0 or end <= start:
        return []

    try:
        parsed = json.loads(content[start : end + 1])
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _sanitize_event_text(value: Any) -> str:
    if not isinstance(value, str):
        return ''
    return ' '.join(value.strip().split())


def _parse_event_type(raw: Any) -> TimelineEventType:
    if not isinstance(raw, str):
        return TimelineEventType.other
    normalized = raw.strip().lower()
    for member in TimelineEventType:
        if member.value == normalized:
            return member
    return TimelineEventType.other


def extract_events_from_text(
    text: str,
    session_id: str = 'default',
    chunk_index: int = 0,
    chunk_start_time: float = 0.0,
    speaker_name: str | None = None,
    player_id: str | None = None,
) -> list[TimelineEvent]:
    entities = _extract_entities_with_local_llm(text)

    if not text.strip():
        return []

    try:
        from app.core.config import settings

        llm_model = settings.llm_model
        ollama_url = settings.ollama_url
    except Exception:
        llm_model = 'hf.co/bartowski/mistralai_Ministral-3-3B-Instruct-2512-GGUF:Q5_K_M'
        ollama_url = 'http://localhost:11434'

    payload = {
        'model': llm_model,
        'stream': False,
        'messages': [
            {'role': 'system', 'content': EVENT_EXTRACTION_PROMPT},
            {
                'role': 'user',
                'content': f'Analyze this transcript segment and extract events:\n\nTEXT:\n{text}',
            },
        ],
    }

    try:
        request = Request(
            f'{ollama_url}/api/chat',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=30.0) as response:
            response_json = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []

    message = response_json.get('message', {})
    content = message.get('content', '') if isinstance(message, dict) else ''
    raw_events = _safe_json_from_llm_response(content)

    events = []
    for i, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            continue
        title = _sanitize_event_text(raw.get('title'))
        description = _sanitize_event_text(raw.get('description'))
        if not title or not description:
            continue

        event = TimelineEvent(
            id='',
            session_id=session_id,
            title=title,
            description=description,
            event_type=_parse_event_type(raw.get('event_type')),
            order=chunk_index + i,
            timestamp=chunk_start_time,
            transcription_chunk_id=f'chunk_{chunk_index}',
            player_id=player_id,
            speaker_name=speaker_name,
            temporal_entities=_dedupe_preserving_order(entities.temporal_entities),
            location_entities=_dedupe_preserving_order(entities.location_entities),
        )
        events.append(event)

    return events


def extract_events_from_transcriptions(
    texts: list[str], speakers: list[str] | None = None, session_id: str = 'default'
) -> list[TimelineEvent]:
    all_events: list[TimelineEvent] = []
    for i, text in enumerate(texts):
        if not text.strip():
            continue
        speaker = speakers[i] if speakers and i < len(speakers) else None
        events = extract_events_from_text(
            text=text, session_id=session_id, chunk_index=i, speaker_name=speaker
        )
        all_events.extend(events)
    return all_events
