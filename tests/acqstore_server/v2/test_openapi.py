"""OpenAPI coverage for side-by-side v1 and v2 APIs."""

from fastapi.testclient import TestClient

from acqstore_server.app import create_app


def test_openapi_contains_frozen_v1_and_typed_v2_routes() -> None:
    body = TestClient(create_app()).get('/openapi.json').json()
    paths = body['paths']
    assert '/api/v1/open' in paths
    assert '/api/v2/open' in paths
    assert '/api/v2/pick-and-open' in paths
    assert '/api/v2/sessions/{session_id}/channels/{channel_index}/data' in paths
    schema = paths['/api/v2/open']['post']['requestBody']['content']['application/json']['schema']
    assert schema['$ref'].endswith('/OpenRequest')


def test_v2_openapi_includes_session_lifecycle_routes() -> None:
    document = TestClient(create_app()).get('/openapi.json').json()
    session_path = document['paths']['/api/v2/sessions/{session_id}']
    assert 'get' in session_path
    assert 'delete' in session_path
    assert session_path['get']['responses']['200']['content']['application/json']['schema']
    assert session_path['delete']['responses']['200']['content']['application/json']['schema']


def test_v2_openapi_includes_capabilities_route() -> None:
    document = TestClient(create_app()).get('/openapi.json').json()
    operation = document['paths']['/api/v2/capabilities']['get']
    assert operation['responses']['200']['content']['application/json']['schema']


def test_v2_openapi_is_descriptive_for_generated_clients() -> None:
    document = TestClient(create_app()).get('/openapi.json').json()
    paths = document['paths']

    assert '/api/v2' in paths
    assert paths['/api/v2']['get']['summary'] == 'Discover API v2 resources'
    assert paths['/api/v2/open']['post']['summary'] == 'Open an acquisition path'

    binary_operation = paths['/api/v2/sessions/{session_id}/channels/{channel_index}/data']['get']
    binary_schema = binary_operation['responses']['200']['content']['application/octet-stream']['schema']
    assert binary_schema == {'type': 'string', 'format': 'binary'}

    open_request = document['components']['schemas']['OpenRequest']
    assert open_request['examples'][0] == {'path': '/data/example.oir'}
    assert open_request['additionalProperties'] is False


def test_v2_openapi_documents_validation_error_envelope() -> None:
    document = TestClient(create_app()).get('/openapi.json').json()
    operation = document['paths']['/api/v2/open']['post']

    validation_schema = operation['responses']['422']['content']['application/json']['schema']
    assert validation_schema['$ref'].endswith('/ErrorResponse')

    error_schema = document['components']['schemas']['ErrorResponse']
    assert error_schema['properties']['details']['anyOf'][0]['items']['$ref'].endswith(
        '/ErrorDetailResponse'
    )
