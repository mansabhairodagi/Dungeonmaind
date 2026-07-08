import asyncio
from uuid import uuid4
from collections import defaultdict
from app.domain.models import TimelineEvent


class TimelineStore:
    def __init__(self) -> None:
        self._events: dict[str, TimelineEvent] = {}
        self._by_session: dict[str, list[str]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def _generate_id(self) -> str:
        return uuid4().hex[:12]

    async def add_event(self, event: TimelineEvent) -> TimelineEvent:
        async with self._lock:
            if not event.id:
                event_id = self._generate_id()
                object.__setattr__(event, "id", event_id)
            else:
                event_id = event.id
            self._events[event_id] = event
            if event.session_id not in self._by_session[event.session_id]:
                self._by_session[event.session_id].append(event_id)
            return event

    async def add_events(self, events: list[TimelineEvent]) -> list[TimelineEvent]:
        async with self._lock:
            added = []
            for event in events:
                if not event.id:
                    event_id = self._generate_id()
                    object.__setattr__(event, "id", event_id)
                else:
                    event_id = event.id
                self._events[event_id] = event
                self._by_session[event.session_id].append(event_id)
                added.append(event)
            return added

    async def get_event(self, event_id: str) -> TimelineEvent | None:
        async with self._lock:
            return self._events.get(event_id)

    async def get_session_events(self, session_id: str = "default") -> list[TimelineEvent]:
        async with self._lock:
            event_ids = list(self._by_session.get(session_id, []))
            events = [self._events[eid] for eid in event_ids if eid in self._events]
            events.sort(key=lambda e: e.order)
            return events

    async def delete_event(self, event_id: str) -> bool:
        async with self._lock:
            event = self._events.pop(event_id, None)
            if event is None:
                return False
            session_events = self._by_session.get(event.session_id, [])
            if event_id in session_events:
                session_events.remove(event_id)
            return True

    async def clear_session(self, session_id: str = "default") -> int:
        async with self._lock:
            event_ids = list(self._by_session.get(session_id, []))
            count = 0
            for eid in event_ids:
                if eid in self._events:
                    del self._events[eid]
                    count += 1
            self._by_session[session_id] = []
            return count

    async def clear_all(self) -> int:
        async with self._lock:
            count = len(self._events)
            self._events.clear()
            self._by_session.clear()
            return count


timeline_store = TimelineStore()
