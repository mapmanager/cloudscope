"""Smoke tests for CloudScope application entry point."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from cloudscope.runtime import reset_runtime_registry_for_tests


@pytest.fixture(autouse=True)
def _clear_runtime_registry() -> None:
    reset_runtime_registry_for_tests()
    yield
    reset_runtime_registry_for_tests()


@pytest.fixture
def _web_run_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the web-server path in ``main()`` (not Option C desktop)."""
    monkeypatch.setenv('CLOUDSCOPE_REMOTE', '1')
    monkeypatch.setenv('CLOUDSCOPE_NATIVE', '0')
    monkeypatch.setenv('CLOUDSCOPE_RELOAD', '0')
    monkeypatch.delenv('CLOUDSCOPE_MULTI_WINDOW', raising=False)
    monkeypatch.delenv('CLOUDSCOPE_DESKTOP_LAUNCHER', raising=False)


def _app_module() -> Any:
    """Import ``cloudscope.app`` lazily to avoid configuring logging at collection time."""
    import cloudscope.app as app_module

    return app_module


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('1', True),
        ('true', True),
        ('yes', True),
        ('0', False),
        ('false', False),
        ('off', False),
    ],
)
def test_parse_bool_env_accepts_known_values(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    expected: bool,
) -> None:
    monkeypatch.setenv('TEST_BOOL', raw)
    assert _app_module()._parse_bool_env('TEST_BOOL', default=not expected) is expected


def test_parse_bool_env_uses_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('TEST_BOOL', raising=False)
    app = _app_module()
    assert app._parse_bool_env('TEST_BOOL', default=True) is True
    assert app._parse_bool_env('TEST_BOOL', default=False) is False


def test_parse_bool_env_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('TEST_BOOL', 'maybe')
    with pytest.raises(ValueError, match='Invalid boolean'):
        _app_module()._parse_bool_env('TEST_BOOL', default=False)


def test_parse_int_env_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('TEST_INT', raising=False)
    assert _app_module()._parse_int_env('TEST_INT') is None


def test_parse_int_env_parses_integer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('TEST_INT', '4242')
    assert _app_module()._parse_int_env('TEST_INT') == 4242


def test_get_run_config_from_env_remote_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CLOUDSCOPE_REMOTE', '1')
    monkeypatch.delenv('CLOUDSCOPE_NATIVE', raising=False)
    monkeypatch.delenv('CLOUDSCOPE_HOST', raising=False)
    monkeypatch.delenv('PORT', raising=False)
    monkeypatch.delenv('CLOUDSCOPE_PORT', raising=False)

    config = _app_module().get_run_config_from_env()

    assert config.remote is True
    assert config.native is False
    assert config.show is False
    assert config.host == '0.0.0.0'
    assert config.port == 8080
    assert config.reload is False


def test_get_run_config_from_env_prefers_platform_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CLOUDSCOPE_REMOTE', '1')
    monkeypatch.setenv('PORT', '9000')
    monkeypatch.setenv('CLOUDSCOPE_PORT', '7000')

    config = _app_module().get_run_config_from_env()

    assert config.port == 9000


def test_get_run_config_from_env_show_defaults_to_true_for_local_web(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('CLOUDSCOPE_REMOTE', raising=False)
    monkeypatch.delenv('CLOUDSCOPE_SHOW', raising=False)
    monkeypatch.setenv('CLOUDSCOPE_NATIVE', '0')

    config = _app_module().get_run_config_from_env()

    assert config.show is True


def test_cloud_scope_run_config_ui_run_kwargs_includes_explicit_host_and_port() -> None:
    app = _app_module()
    config = app.CloudScopeRunConfig(
        host='127.0.0.1',
        port=4242,
        native=False,
        reload=False,
        remote=True,
        storage_secret='test-secret',
        show=False,
    )

    kwargs = config.ui_run_kwargs()

    assert kwargs['title'] == 'CloudScope'
    assert kwargs['native'] is False
    assert kwargs['reload'] is False
    assert kwargs['storage_secret'] == 'test-secret'
    assert kwargs['show'] is False
    assert kwargs['host'] == '127.0.0.1'
    assert kwargs['port'] == 4242


def test_main_calls_ui_run_for_web_mode(
    monkeypatch: pytest.MonkeyPatch,
    _web_run_env: None,
) -> None:
    captured: list[dict[str, object]] = []

    def _fake_ui_run(**kwargs: object) -> None:
        captured.append(kwargs)

    monkeypatch.setattr('nicegui.ui.run', _fake_ui_run)

    _app_module().main()

    assert len(captured) == 1
    assert captured[0]['native'] is False
    assert captured[0]['title'] == 'CloudScope'


def test_main_uses_option_c_desktop_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('CLOUDSCOPE_NATIVE', '1')
    monkeypatch.setenv('CLOUDSCOPE_MULTI_WINDOW', '1')
    monkeypatch.delenv('CLOUDSCOPE_SINGLE_WINDOW', raising=False)
    called: list[bool] = []

    monkeypatch.setattr(
        'cloudscope.desktop_launcher.run_option_c_desktop',
        lambda config: called.append(True),
    )

    def _fail_ui_run(**_kwargs: object) -> None:
        raise AssertionError('ui.run should not be called for Option C desktop')

    monkeypatch.setattr('nicegui.ui.run', _fail_ui_run)

    _app_module().main()

    assert called == [True]


def test_configure_native_window_noop_when_not_native() -> None:
    app = _app_module()
    config = app.CloudScopeRunConfig(
        host=None,
        port=None,
        native=False,
        reload=False,
        remote=False,
        storage_secret='test-secret',
        show=False,
    )
    app.configure_native_window(config)


def _free_tcp_port() -> int:
    """Return an ephemeral localhost port for subprocess smoke tests.

    Returns:
        Available TCP port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def test_app_py_serves_home_page_over_http() -> None:
    """Start ``app.py`` as a real server and verify the home page responds."""
    port = _free_tcp_port()
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('PYTEST') or key.startswith('NICEGUI_SCREEN'):
            env.pop(key)
    env.update({
        'CLOUDSCOPE_NATIVE': '0',
        'CLOUDSCOPE_RELOAD': '0',
        'CLOUDSCOPE_SHOW': '0',
        'CLOUDSCOPE_HOST': '127.0.0.1',
        'CLOUDSCOPE_PORT': str(port),
    })
    app_path = Path('src/cloudscope/app.py').resolve()
    proc = subprocess.Popen(
        [sys.executable, str(app_path)],
        env=env,
        cwd=Path.cwd(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30.0
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                response = httpx.get(f'http://127.0.0.1:{port}/', timeout=1.0)
            except httpx.HTTPError as exc:
                last_error = exc
                if proc.poll() is not None:
                    break
                time.sleep(0.2)
                continue
            assert response.status_code == 200
            assert 'CloudScope' in response.text
            return
        if proc.poll() is not None:
            raise AssertionError(f'app.py exited early with code {proc.returncode}') from last_error
        raise AssertionError('Timed out waiting for app.py to serve the home page') from last_error
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
