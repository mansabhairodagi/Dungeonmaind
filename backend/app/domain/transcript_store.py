"""Async-safe in-memory store for a session's transcript segments."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    """One transcribed stretch of speech in a session recording.

    Attributes:
        start: Start time of the segment in seconds.
        end: End time of the segment in seconds.
        text: Transcribed text of the segment.
        speaker: Speaker label or player name assigned to the segment.
    """

    start: float
    end: float
    text: str
    speaker: str = 'unknown'

    def to_dict(self) -> dict:
        """Serialize this segment for transcript.json."""
        return {'start': self.start, 'end': self.end, 'text': self.text, 'speaker': self.speaker}

    @classmethod
    def from_dict(cls, data: dict) -> TranscriptSegment:
        """Deserialize a segment written by export."""
        return cls(
            start=float(data['start']),
            end=float(data['end']),
            text=str(data['text']),
            speaker=str(data.get('speaker') or 'unknown'),
        )


class TranscriptStore:
    """Async-safe in-memory store for transcript segments, per session.

    Segment times are on one clock per session: each uploaded or recorded
    chunk is placed after the audio already received for that session, so
    a start time points at the same moment in the session's full recording.

    Attributes:
        _segments: Dict mapping session ID to its segments in arrival order.
        _audio_end: Dict mapping session ID to the end (seconds) of the audio
            received so far.
        _lock: Async lock for thread-safe access.
    """

    def __init__(self) -> None:
        self._segments: dict[str, list[TranscriptSegment]] = {}
        self._audio_end: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def reserve_audio_span(self, session_id: str, seconds: float) -> float:
        """Place a newly received audio chunk at the end of the session's audio.

        A session with no recorded clock yet (for example one loaded from
        transcript.json) continues after its last saved segment.

        Args:
            session_id: The session identifier.
            seconds: Length of the new chunk in seconds.

        Returns:
            Offset in seconds where the new chunk starts in the session.
        """
        async with self._lock:
            offset = self._audio_end.get(session_id)
            if offset is None:
                offset = max((seg.end for seg in self._segments.get(session_id, [])), default=0.0)
            self._audio_end[session_id] = offset + max(0.0, seconds)
            return offset

    async def add_segments(self, session_id: str, segments: list[TranscriptSegment]) -> None:
        """Append segments to a session's transcript.

        Args:
            session_id: The session identifier.
            segments: Segments to append, in spoken order.
        """
        async with self._lock:
            self._segments.setdefault(session_id, []).extend(segments)

    async def get_segments(self, session_id: str) -> list[TranscriptSegment]:
        """Get a copy of a session's transcript segments.

        Args:
            session_id: The session identifier.

        Returns:
            The session's segments in arrival order (empty if none).
        """
        async with self._lock:
            return list(self._segments.get(session_id, []))

    async def replace_session(self, session_id: str, segments: list[TranscriptSegment]) -> None:
        """Replace every segment for one session with the given list.

        Args:
            session_id: The session identifier.
            segments: Segments that should exist for this session after the call.
        """
        async with self._lock:
            self._segments[session_id] = list(segments)
            self._audio_end.pop(session_id, None)

    async def rename_session(self, old_session_id: str, new_session_id: str) -> None:
        """Move a session's transcript to a new session ID.

        Any transcript already stored under the new ID is replaced. Does
        nothing when both IDs are equal.

        Args:
            old_session_id: The session identifier the segments are stored under.
            new_session_id: The session identifier they should be stored under.
        """
        if old_session_id == new_session_id:
            return
        async with self._lock:
            self._segments[new_session_id] = self._segments.pop(old_session_id, [])
            self._audio_end.pop(new_session_id, None)
            if old_session_id in self._audio_end:
                self._audio_end[new_session_id] = self._audio_end.pop(old_session_id)

    async def clear_session(self, session_id: str) -> int:
        """Clear a session's transcript.

        Args:
            session_id: The session identifier.

        Returns:
            The number of segments removed.
        """
        async with self._lock:
            self._audio_end.pop(session_id, None)
            return len(self._segments.pop(session_id, []))


transcript_store = TranscriptStore()
