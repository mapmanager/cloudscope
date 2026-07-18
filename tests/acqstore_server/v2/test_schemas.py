"""Contract tests for AcqStore Server API v2 Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from acqstore_server.v2.schemas import (
    AxisResponse,
    ChannelResponse,
    HeaderResponse,
    OpenRequest,
    OpenResponse,
    PickAndOpenRequest,
    PlaneResponse,
    SourceResponse,
)


def test_open_request_accepts_camel_case_and_preserves_channel_order() -> None:
    request = OpenRequest.model_validate(
        {'path': '/tmp/example.oir', 'channelIndices': [2, 0, 1]}
    )
    assert request.path == '/tmp/example.oir'
    assert request.channel_indices == [2, 0, 1]


def test_open_request_omitted_channel_indices_means_all_channels() -> None:
    request = OpenRequest.model_validate({'path': '/tmp/example.oir'})
    assert request.channel_indices is None


@pytest.mark.parametrize(
    'channel_indices',
    [[], [0, 0], [-1], [0, -1]],
)
def test_open_request_rejects_invalid_channel_indices(
    channel_indices: list[int],
) -> None:
    with pytest.raises(ValidationError):
        OpenRequest.model_validate(
            {'path': '/tmp/example.oir', 'channelIndices': channel_indices}
        )


def test_open_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        OpenRequest.model_validate(
            {'path': '/tmp/example.oir', 'calciumChannel': 0}
        )


@pytest.mark.parametrize('path', ['', '   '])
def test_open_request_rejects_blank_path(path: str) -> None:
    with pytest.raises(ValidationError):
        OpenRequest.model_validate({'path': path})


def test_pick_request_normalizes_extensions() -> None:
    request = PickAndOpenRequest.model_validate(
        {'channelIndices': [1], 'extensions': ['oir', '.czi']}
    )
    assert request.extensions == ['.oir', '.czi']


@pytest.mark.parametrize('extensions', [[], [''], ['  '], ['oir', '.oir']])
def test_pick_request_rejects_invalid_extensions(extensions: list[str]) -> None:
    with pytest.raises(ValidationError):
        PickAndOpenRequest.model_validate({'extensions': extensions})


def test_open_response_serializes_json_contract_in_camel_case() -> None:
    plane = PlaneResponse(
        shape=(5, 4),
        axes=[
            AxisResponse(
                array_dimension=0,
                name='Y',
                size=5,
                step=0.001,
                unit='seconds',
            ),
            AxisResponse(
                array_dimension=1,
                name='X',
                size=4,
                step=0.2,
                unit='micrometer',
            ),
        ],
    )
    response = OpenResponse(
        session_id='abc123',
        source=SourceResponse(
            path='/tmp/example.oir',
            name='example.oir',
            format='oir',
            source_dtype='uint16',
            num_channels=2,
        ),
        header=HeaderResponse(
            shape=[2, 5, 4],
            dims=['C', 'Y', 'X'],
            sizes={'C': 2, 'Y': 5, 'X': 4},
            dtype='uint16',
            num_channels=2,
            physical_units=[1.0, 0.001, 0.2],
            physical_units_labels=['Channels', 'seconds', 'micrometer'],
            date='',
            time='',
            file_size='1.2 MB',
        ),
        plane=plane,
        channels=[
            ChannelResponse(
                index=0,
                name='CH1',
                byte_length=80,
                data_url='/api/v2/sessions/abc123/channels/0/data',
            )
        ],
    )

    payload = response.model_dump(by_alias=True, mode='json')
    assert payload['sessionId'] == 'abc123'
    assert payload['source']['sourceDtype'] == 'uint16'
    assert payload['source']['numChannels'] == 2
    assert payload['header']['dims'] == ['C', 'Y', 'X']
    assert payload['header']['physicalUnits'][1] == 0.001
    assert payload['plane']['servedDtype'] == 'float32'
    assert payload['plane']['axes'][0]['arrayDimension'] == 0
    assert payload['channels'][0]['byteLength'] == 80
    assert payload['channels'][0]['dataUrl'].endswith('/channels/0/data')
    assert 'session_id' not in payload
