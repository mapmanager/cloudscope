"""Server-boundary tests using deterministic opened-acquisition results.

The filename is retained so replacement merges overwrite Ticket 010's optional
real-format tests. Format decoding belongs to AcqStore's own test suite.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest
from fastapi.testclient import TestClient

from acqstore_server.app import create_app
from acqstore_server.v2.models import OpenedAcquisition
from acqstore_server.v2.session_store import SessionStore
from tests.acqstore_server.v2.representative_files import opened_acquisition_fixture


@pytest.mark.parametrize('format_name', ['tif', 'oir', 'czi', 'nd2'])
def test_server_serializes_transport_neutral_open_result(format_name: str) -> None:
    """A format label must not change the generic HTTP transport contract."""
    calls: list[tuple[str, Sequence[int] | None]] = []

    def fake_open(
        path: str,
        *,
        channel_indices: Sequence[int] | None = None,
    ) -> OpenedAcquisition:
        calls.append((path, channel_indices))
        requested = tuple(channel_indices) if channel_indices is not None else (0, 1)
        return opened_acquisition_fixture(
            path,
            format_name=format_name,
            channel_indices=requested,
        )

    client = TestClient(
        create_app(
            v2_session_store=SessionStore(ttl_seconds=60.0),
            v2_open_fn=fake_open,
        )
    )
    response = client.post(
        '/api/v2/open',
        json={'path': f'/virtual/sample.{format_name}', 'channelIndices': [1, 0]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert calls == [(f'/virtual/sample.{format_name}', [1, 0])]
    assert payload['source']['format'] == format_name
    assert payload['plane']['shape'] == [5, 4]
    assert [channel['index'] for channel in payload['channels']] == [1, 0]

    for channel in payload['channels']:
        binary = client.get(channel['dataUrl'])
        assert binary.status_code == 200
        decoded = np.frombuffer(binary.content, dtype='<f4').reshape(5, 4)
        assert decoded.dtype == np.float32
        assert decoded.shape == (5, 4)


def test_server_forwards_channel_selection_to_open_boundary() -> None:
    received: list[Sequence[int] | None] = []

    def fake_open(
        path: str,
        *,
        channel_indices: Sequence[int] | None = None,
    ) -> OpenedAcquisition:
        received.append(channel_indices)
        return opened_acquisition_fixture(path, channel_indices=(2,))

    client = TestClient(create_app(v2_open_fn=fake_open))
    response = client.post(
        '/api/v2/open',
        json={'path': '/virtual/source.oir', 'channelIndices': [2]},
    )

    assert response.status_code == 200
    assert received == [[2]]
    assert [channel['index'] for channel in response.json()['channels']] == [2]
