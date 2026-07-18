"""Tests for generic API v2 binary session storage."""

from __future__ import annotations

import time

import pytest

from acqstore_server.v2.session_store import SessionBuffers, SessionStore


def test_store_supports_arbitrary_source_channel_indices() -> None:
    store = SessionStore()
    session_id = store.create(SessionBuffers(channels={0: b'zero', 2: b'two', 7: b'seven'}))

    assert store.get_channel(session_id, 0) == b'zero'
    assert store.get_channel(session_id, 2) == b'two'
    assert store.get_channel(session_id, 7) == b'seven'
    assert store.get_channel(session_id, 1) is None


def test_source_and_reference_channel_namespaces_do_not_collide() -> None:
    store = SessionStore()
    session_id = store.create(
        SessionBuffers(
            channels={0: b'source-zero'},
            reference_channels={0: b'reference-zero', 3: b'reference-three'},
        )
    )

    assert store.get_channel(session_id, 0) == b'source-zero'
    assert store.get_reference_channel(session_id, 0) == b'reference-zero'
    assert store.get_reference_channel(session_id, 3) == b'reference-three'
    assert store.get_channel(session_id, 3) is None


def test_missing_session_returns_none() -> None:
    store = SessionStore()
    assert store.get_channel('missing', 0) is None
    assert store.get_reference_channel('missing', 0) is None


def test_session_expires() -> None:
    store = SessionStore(ttl_seconds=0.01)
    session_id = store.create(SessionBuffers(channels={0: b'data'}))
    time.sleep(0.03)
    assert store.get_channel(session_id, 0) is None


@pytest.mark.parametrize('ttl_seconds', [0.0, -1.0])
def test_ttl_must_be_positive(ttl_seconds: float) -> None:
    with pytest.raises(ValueError):
        SessionStore(ttl_seconds=ttl_seconds)


@pytest.mark.parametrize('channel_index', [-1, True, '0'])
def test_buffers_reject_invalid_channel_keys(channel_index: object) -> None:
    with pytest.raises(ValueError):
        SessionBuffers(channels={channel_index: b'data'})  # type: ignore[dict-item]


def test_buffers_reject_non_bytes_payload() -> None:
    with pytest.raises(TypeError):
        SessionBuffers(channels={0: bytearray(b'data')})  # type: ignore[dict-item]


def test_buffers_defensively_copy_input_mappings() -> None:
    channels = {0: b'original'}
    buffers = SessionBuffers(channels=channels)
    channels[0] = b'mutated'
    assert buffers.channels[0] == b'original'


def test_describe_reports_indices_size_and_remaining_ttl() -> None:
    store = SessionStore(ttl_seconds=30.0)
    session_id = store.create(
        SessionBuffers(
            channels={2: b'ab', 0: b'c'},
            reference_channels={4: b'def'},
        )
    )

    description = store.describe(session_id)

    assert description is not None
    assert description.session_id == session_id
    assert description.channel_indices == (0, 2)
    assert description.reference_channel_indices == (4,)
    assert description.total_bytes == 6
    assert 0 < description.ttl_seconds_remaining <= 30.0


def test_delete_removes_session_and_is_idempotently_false() -> None:
    store = SessionStore()
    session_id = store.create(SessionBuffers(channels={0: b'data'}))

    assert store.delete(session_id) is True
    assert store.has_session(session_id) is False
    assert store.describe(session_id) is None
    assert store.delete(session_id) is False
