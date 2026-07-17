"""Generic short-lived binary session storage for AcqStore Server API v2."""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class SessionBuffers:
    """Binary payloads indexed by source or reference channel number."""

    channels: Mapping[int, bytes]
    reference_channels: Mapping[int, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'channels', self._validated_copy(self.channels, 'channels'))
        object.__setattr__(
            self,
            'reference_channels',
            self._validated_copy(self.reference_channels, 'reference_channels'),
        )

    @staticmethod
    def _validated_copy(values: Mapping[int, bytes], name: str) -> Mapping[int, bytes]:
        copied: dict[int, bytes] = {}
        for index, payload in values.items():
            if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                raise ValueError(f'{name} keys must be non-negative integers, got {index!r}')
            if not isinstance(payload, bytes):
                raise TypeError(f'{name}[{index}] must be bytes, got {type(payload).__name__}')
            copied[index] = payload
        return MappingProxyType(copied)


@dataclass(frozen=True, slots=True)
class SessionDescription:
    """Metadata describing one unexpired session without exposing payloads."""

    session_id: str
    ttl_seconds_remaining: float
    channel_indices: tuple[int, ...]
    reference_channel_indices: tuple[int, ...]
    total_bytes: int


@dataclass(frozen=True, slots=True)
class _SessionEntry:
    buffers: SessionBuffers
    expires_at: float


class SessionStore:
    """Thread-safe in-memory v2 session map with TTL expiry."""

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        if ttl_seconds <= 0:
            raise ValueError(f'ttl_seconds must be positive, got {ttl_seconds}')
        self._ttl_seconds = float(ttl_seconds)
        self._lock = threading.Lock()
        self._sessions: dict[str, _SessionEntry] = {}

    @property
    def ttl_seconds(self) -> float:
        """Return the session time-to-live in seconds."""
        return self._ttl_seconds

    def create(self, buffers: SessionBuffers) -> str:
        """Store buffers and return a new opaque session identifier."""
        session_id = secrets.token_hex(16)
        now = time.monotonic()
        entry = _SessionEntry(buffers=buffers, expires_at=now + self._ttl_seconds)
        with self._lock:
            self._purge_expired_unlocked(now)
            self._sessions[session_id] = entry
        return session_id

    def has_session(self, session_id: str) -> bool:
        """Return whether an unexpired session exists."""
        return self._get_entry(session_id) is not None

    def describe(self, session_id: str) -> SessionDescription | None:
        """Return metadata for one unexpired session, or ``None``."""
        now = time.monotonic()
        with self._lock:
            self._purge_expired_unlocked(now)
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            buffers = entry.buffers
            return SessionDescription(
                session_id=session_id,
                ttl_seconds_remaining=max(0.0, entry.expires_at - now),
                channel_indices=tuple(sorted(buffers.channels)),
                reference_channel_indices=tuple(sorted(buffers.reference_channels)),
                total_bytes=(
                    sum(len(payload) for payload in buffers.channels.values())
                    + sum(len(payload) for payload in buffers.reference_channels.values())
                ),
            )

    def delete(self, session_id: str) -> bool:
        """Delete one session and return whether it existed and was unexpired."""
        now = time.monotonic()
        with self._lock:
            self._purge_expired_unlocked(now)
            return self._sessions.pop(session_id, None) is not None

    def get_channel(self, session_id: str, channel_index: int) -> bytes | None:
        """Return one source channel payload, or ``None`` when unavailable."""
        entry = self._get_entry(session_id)
        return None if entry is None else entry.buffers.channels.get(channel_index)

    def get_reference_channel(self, session_id: str, channel_index: int) -> bytes | None:
        """Return one reference channel payload, or ``None`` when unavailable."""
        entry = self._get_entry(session_id)
        return None if entry is None else entry.buffers.reference_channels.get(channel_index)

    def _get_entry(self, session_id: str) -> _SessionEntry | None:
        with self._lock:
            self._purge_expired_unlocked(time.monotonic())
            return self._sessions.get(session_id)

    def _purge_expired_unlocked(self, now: float) -> None:
        expired = [session_id for session_id, entry in self._sessions.items() if entry.expires_at <= now]
        for session_id in expired:
            del self._sessions[session_id]
