"""Regression checks for the public API v2 OpenAPI contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

from acqstore_server.app import create_app


def _openapi() -> dict[str, object]:
    response = TestClient(create_app()).get('/openapi.json')
    assert response.status_code == 200
    return response.json()


def test_openapi_exposes_javascript_client_lifecycle() -> None:
    document = _openapi()
    paths = document['paths']

    expected_operations = {
        '/api/v2': {'get'},
        '/api/v2/health': {'get'},
        '/api/v2/capabilities': {'get'},
        '/api/v2/open': {'post'},
        '/api/v2/pick-and-open': {'post'},
        '/api/v2/sessions/{session_id}': {'get', 'delete'},
        '/api/v2/sessions/{session_id}/channels/{channel_index}/data': {'get'},
        '/api/v2/sessions/{session_id}/reference/channels/{channel_index}/data': {'get'},
    }

    for path, methods in expected_operations.items():
        assert path in paths
        assert methods <= set(paths[path])


def test_openapi_keeps_v2_json_models_camel_case() -> None:
    schemas = _openapi()['components']['schemas']

    api_index = schemas['ApiIndexResponse']['properties']
    assert 'apiVersion' in api_index
    assert 'api_version' not in api_index

    open_response = schemas['OpenResponse']['properties']
    assert 'sessionId' in open_response
    assert 'session_id' not in open_response

    header = schemas['HeaderResponse']['properties']
    assert {'numChannels', 'physicalUnits', 'physicalUnitsLabels', 'fileSize'} <= set(header)
    assert 'num_channels' not in header

    channel = schemas['ChannelResponse']['properties']
    assert {'byteLength', 'dataUrl'} <= set(channel)
    assert 'byte_length' not in channel
    assert 'data_url' not in channel

    plane = schemas['PlaneResponse']['properties']
    assert 'servedDtype' in plane
    assert 'served_dtype' not in plane

    axis = schemas['AxisResponse']['properties']
    assert 'arrayDimension' in axis
    assert 'array_dimension' not in axis

    binary = schemas['BinaryEncodingResponse']['properties']
    assert {'servedDtype', 'mediaType'} <= set(binary)


def test_openapi_documents_binary_responses() -> None:
    paths = _openapi()['paths']
    binary_paths = (
        '/api/v2/sessions/{session_id}/channels/{channel_index}/data',
        '/api/v2/sessions/{session_id}/reference/channels/{channel_index}/data',
    )

    for path in binary_paths:
        response_200 = paths[path]['get']['responses']['200']
        content = response_200['content']
        assert 'application/octet-stream' in content
        assert content['application/octet-stream']['schema'] == {
            'type': 'string',
            'format': 'binary',
        }
