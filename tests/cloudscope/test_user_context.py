"""Tests for CloudScope user/workspace context resolution."""

from __future__ import annotations

import os

from cloudscope.app_config import AppConfigData
from cloudscope.user_context import (
    LAST_USED_FILE_NAME,
    UserContextKind,
    cleanup_expired_demo_sessions,
    resolve_user_context,
    resolve_user_context_from_env,
    safe_user_id,
)


def test_safe_user_id_normalizes_email_like_identity() -> None:
    assert safe_user_id('Robert.Cudmore+Demo@Example.ORG') == 'robert.cudmore_demo_example.org'


def test_local_context_uses_platformdirs_and_persistent_config() -> None:
    context = resolve_user_context(remote=False, native=True)

    assert context.kind is UserContextKind.LOCAL_OS_USER
    assert context.user_id == 'local'
    assert context.config_path.name == 'app_config.json'
    assert context.upload_dir.name == 'uploads'
    assert context.sample_data_dir.name == 'sample-data'
    assert context.persistent is True
    assert context.quota.quota_bytes is None


def test_server_demo_context_is_ephemeral_under_data_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv('CLOUDSCOPE_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('CLOUDSCOPE_DEMO_SESSION_QUOTA_MB', '2')
    monkeypatch.setenv('CLOUDSCOPE_DEMO_MAX_UPLOAD_MB', '1')
    context = resolve_user_context(remote=True, native=False, demo_session_id='Demo Session 1')

    assert context.kind is UserContextKind.SERVER_DEMO
    assert context.user_id == 'demo_session_1'
    assert context.data_dir == tmp_path / 'tmp' / 'demo-sessions' / 'demo_session_1'
    assert context.upload_dir == context.data_dir / 'uploads'
    assert context.sample_data_dir == tmp_path / 'shared' / 'sample-data'
    assert context.persistent is False
    assert context.quota.quota_bytes == 2 * 1024 * 1024
    assert context.quota.max_upload_bytes == 1 * 1024 * 1024
    assert context.last_used_path == context.data_dir / LAST_USED_FILE_NAME
    assert context.last_used_path.exists()

    config = context.load_app_config()
    config.data.last_path = '/tmp/should-not-persist.tif'
    config.save()
    assert config.persistent is False
    assert not context.config_path.exists()


def test_server_auth_context_is_persistent_under_users_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv('CLOUDSCOPE_DATA_DIR', str(tmp_path))
    context = resolve_user_context(remote=True, native=False, auth_user_id='me@example.org')

    assert context.kind is UserContextKind.SERVER_AUTH_USER
    assert context.user_id == 'me_example.org'
    assert context.data_dir == tmp_path / 'users' / 'me_example.org'
    assert context.config_path == context.data_dir / 'app_config.json'
    assert context.upload_dir == context.data_dir / 'uploads'
    assert context.persistent is True

    config = context.load_app_config()
    assert isinstance(config.data, AppConfigData)
    config.data.last_path = ''
    config.save()
    assert context.config_path.exists()


def test_resolve_user_context_from_env_defaults_remote_to_demo(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv('CLOUDSCOPE_REMOTE', '1')
    monkeypatch.setenv('CLOUDSCOPE_NATIVE', '0')
    monkeypatch.setenv('CLOUDSCOPE_DATA_DIR', str(tmp_path))

    context = resolve_user_context_from_env(demo_session_id='abc')

    assert context.kind is UserContextKind.SERVER_DEMO
    assert context.sample_data_dir == tmp_path / 'shared' / 'sample-data'


def test_cleanup_expired_demo_sessions_removes_only_old_sessions(tmp_path) -> None:
    demo_root = tmp_path / 'demo-sessions'
    old_session = demo_root / 'old'
    new_session = demo_root / 'new'
    old_session.mkdir(parents=True)
    new_session.mkdir()
    old_marker = old_session / LAST_USED_FILE_NAME
    new_marker = new_session / LAST_USED_FILE_NAME
    old_marker.write_text('old', encoding='utf-8')
    new_marker.write_text('new', encoding='utf-8')
    os.utime(old_marker, (100.0, 100.0))
    os.utime(new_marker, (1000.0, 1000.0))

    removed = cleanup_expired_demo_sessions(demo_root=demo_root, max_age_seconds=200, now=1000.0)

    assert removed == 1
    assert not old_session.exists()
    assert new_session.exists()
