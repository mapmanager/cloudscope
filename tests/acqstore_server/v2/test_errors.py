"""Stable API v2 error-envelope coverage."""

from __future__ import annotations

from fastapi.testclient import TestClient

from acqstore_server.app import create_app


def test_missing_required_body_field_uses_v2_error_envelope() -> None:
    response = TestClient(create_app()).post('/api/v2/open', json={})

    assert response.status_code == 422
    assert response.json() == {
        'ok': False,
        'error': 'request_validation_failed',
        'message': 'Request validation failed',
        'details': [
            {
                'location': ['body', 'path'],
                'message': 'Field required',
                'type': 'missing',
            }
        ],
    }


def test_schema_validation_errors_are_normalized() -> None:
    response = TestClient(create_app()).post(
        '/api/v2/open',
        json={
            'path': '   ',
            'channelIndices': [1, 1],
            'unexpected': True,
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['ok'] is False
    assert payload['error'] == 'request_validation_failed'
    assert payload['message'] == 'Request validation failed'
    assert {tuple(detail['location']) for detail in payload['details']} == {
        ('body', 'channelIndices'),
        ('body', 'path'),
        ('body', 'unexpected'),
    }


def test_invalid_json_uses_v2_error_envelope() -> None:
    response = TestClient(create_app()).post(
        '/api/v2/open',
        content=b'{not-json',
        headers={'Content-Type': 'application/json'},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['error'] == 'request_validation_failed'
    assert payload['details'][0]['location'][0] == 'body'
    assert payload['details'][0]['type'] == 'json_invalid'


def test_invalid_path_parameter_uses_v2_error_envelope() -> None:
    response = TestClient(create_app()).get(
        '/api/v2/sessions/example/channels/not-an-integer/data'
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload['error'] == 'request_validation_failed'
    assert payload['details'] == [
        {
            'location': ['path', 'channel_index'],
            'message': 'Input should be a valid integer, unable to parse string as an integer',
            'type': 'int_parsing',
        }
    ]


def test_v1_validation_contract_is_not_changed() -> None:
    response = TestClient(create_app()).post('/api/v1/open', json={})

    assert response.status_code == 404
    assert response.json() == {
        'ok': False,
        'error': 'path_not_found',
        'message': 'JSON body must include string "path"',
    }
