"""Short-lived session storage for channel and reference float32 payloads."""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class SessionBuffers:
    """Raw little-endian float32 bytes for one open session."""

    calcium: bytes
    vessels: bytes | None = None
    reference_channels: tuple[bytes, ...] = ()


@dataclass(slots=True)
class SessionEntry:
    """One open session and its expiry."""

    buffers: SessionBuffers
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = 0.0


class SessionStore:
    """Thread-safe in-memory session map with TTL expiry.

    Args:
        ttl_seconds: Seconds a session remains fetchable after create.
    """

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        if ttl_seconds <= 0:
            raise ValueError(f'ttl_seconds must be positive, got {ttl_seconds}')
        self._ttl_seconds = float(ttl_seconds)
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionEntry] = {}

    @property
    def ttl_seconds(self) -> float:
        """Return the session time-to-live in seconds."""
        return self._ttl_seconds

    def create(self, buffers: SessionBuffers) -> str:
        """Store buffers and return a new session id.

        Args:
            buffers: Payloads for this open.

        Returns:
            Opaque session id string.
        """
        sid = secrets.token_hex(16)
        now = time.monotonic()
        entry = SessionEntry(
            buffers=buffers,
            created_at=now,
            expires_at=now + self._ttl_seconds,
        )
        with self._lock:
            self._purge_expired_unlocked(now)
            self._sessions[sid] = entry
        return sid

    def get_channel(self, session_id: str, role: str) -> bytes | None:
        """Return bytes for a channel role, or ``None`` if missing/expired.

        Args:
            session_id: Id returned by :meth:`create`.
            role: ``calcium`` or ``vessels``.

        Returns:
            Raw float32 LE bytes, or ``None``.
        """
        with self._lock:
            self._purge_expired_unlocked(time.monotonic())
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            if role == 'calcium':
                return entry.buffers.calcium
            if role == 'vessels':
                return entry.buffers.vessels
            return None

    def get_reference(self, session_id: str, channel: int = 0) -> bytes | None:
        """Return reference plane bytes for ``channel``, or ``None``.

        Args:
            session_id: Id returned by :meth:`create`.
            channel: Zero-based reference channel index (default ``0``).

        Returns:
            Raw float32 LE bytes, or ``None``.
        """
        with self._lock:
            self._purge_expired_unlocked(time.monotonic())
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            planes = entry.buffers.reference_channels
            if channel < 0 or channel >= len(planes):
                return None
            return planes[channel]

    def _purge_expired_unlocked(self, now: float) -> None:
        expired = [sid for sid, entry in self._sessions.items() if entry.expires_at <= now]
        for sid in expired:
            del self._sessions[sid]
