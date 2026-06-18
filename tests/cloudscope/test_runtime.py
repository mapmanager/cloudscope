"""Tests for CloudScope shared runtime registry."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.runtime import (
    CloudScopeRuntimeRegistry,
    _build_runtime,
    infer_load_kind,
    reset_runtime_registry_for_tests,
    runtime_key_from_user_context,
)
from cloudscope.user_context import UserContext, UserContextKind


@pytest.fixture(autouse=True)
def _clear_runtime_registry() -> None:
    reset_runtime_registry_for_tests()
    yield
    reset_runtime_registry_for_tests()


def _local_context() -> UserContext:
    return UserContext(
        kind=UserContextKind.LOCAL_OS_USER,
        user_id='local',
        config_path=AppConfig.default_config_path(),
        data_dir=AppConfig.default_config_path().parent,
        upload_dir=AppConfig.default_config_path().parent / 'uploads',
        sample_data_dir=AppConfig.default_config_path().parent / 'sample-data',
        cache_dir=AppConfig.default_config_path().parent / 'cache',
    )


def test_same_key_returns_same_runtime_object() -> None:
    registry = CloudScopeRuntimeRegistry()
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)

    runtime_1 = registry.get_or_create('session-a', lambda: _build_runtime(user_context, app_config))
    sentinel = object()
    runtime_1.home_page_controller.state.acq_image_list = sentinel  # type: ignore[assignment]
    runtime_2 = registry.get_or_create('session-a', lambda: _build_runtime(user_context, app_config))

    assert runtime_1 is runtime_2
    assert runtime_2.home_page_controller.state.acq_image_list is sentinel


def test_different_keys_return_different_runtimes() -> None:
    registry = CloudScopeRuntimeRegistry()
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)

    runtime_a = registry.get_or_create('a', lambda: _build_runtime(user_context, app_config))
    runtime_b = registry.get_or_create('b', lambda: _build_runtime(user_context, app_config))

    assert runtime_a is not runtime_b
    assert runtime_a.event_bus is not runtime_b.event_bus


def test_registry_concurrent_get_or_create() -> None:
    registry = CloudScopeRuntimeRegistry()
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    results: list[object] = []

    def worker() -> None:
        runtime = registry.get_or_create('shared', lambda: _build_runtime(user_context, app_config))
        results.append(runtime)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 8
    assert all(result is results[0] for result in results)


def test_runtime_factory_creates_single_event_bus() -> None:
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    runtime = _build_runtime(user_context, app_config)

    assert isinstance(runtime.event_bus, EventBus)
    assert runtime.home_page_controller is not None
    assert runtime.load_save_controller.task_runner is runtime.task_runner


def test_initialize_once_is_idempotent() -> None:
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    runtime = _build_runtime(user_context, app_config)

    runtime.initialize_once()
    files_before = runtime.home_page_controller.state.acq_image_list
    runtime.initialize_once()

    assert runtime.home_page_controller.state.acq_image_list is files_before
    assert runtime.initialized is True


def test_initialize_once_does_not_replace_acq_image_list(monkeypatch: pytest.MonkeyPatch) -> None:
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    runtime = _build_runtime(user_context, app_config)
    sentinel = object()
    runtime.home_page_controller.state.acq_image_list = sentinel  # type: ignore[assignment]

    runtime.initialize_once()

    assert runtime.home_page_controller.state.acq_image_list is sentinel


def test_ensure_controllers_bound_is_idempotent() -> None:
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    runtime = _build_runtime(user_context, app_config)

    runtime.ensure_controllers_bound()
    assert runtime.controllers_bound is True
    runtime.ensure_controllers_bound()
    assert runtime.controllers_bound is True


def test_runtime_key_from_user_context_uses_user_id() -> None:
    user_context = _local_context()
    assert runtime_key_from_user_context(user_context) == 'local'


def test_infer_load_kind_csv() -> None:
    from cloudscope.events.files import LoadPathKind

    assert infer_load_kind('/tmp/list.csv') is LoadPathKind.CSV


def test_infer_load_kind_folder(tmp_path) -> None:
    from cloudscope.events.files import LoadPathKind

    folder = tmp_path / 'folder'
    folder.mkdir()
    assert infer_load_kind(str(folder)) is LoadPathKind.FOLDER


def test_get_current_runtime_uses_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    from cloudscope import runtime as runtime_module

    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    monkeypatch.setattr(runtime_module, 'resolve_runtime_context', lambda: (user_context, app_config))

    runtime_1 = runtime_module.get_current_runtime()
    runtime_2 = runtime_module.get_current_runtime()

    assert runtime_1 is runtime_2


def test_client_disconnect_does_not_clear_registry() -> None:
    registry = CloudScopeRuntimeRegistry()
    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    registry.get_or_create('session-a', lambda: _build_runtime(user_context, app_config))
    assert registry.get('session-a') is not None
    registry.clear()
    assert registry.get('session-a') is None


def test_set_process_app_config_shared_by_resolve_runtime_context() -> None:
    from cloudscope.runtime import (
        clear_process_app_config,
        resolve_runtime_context,
        set_process_app_config,
    )

    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    app_config.set_window_rect(42, 43, 800, 600)

    set_process_app_config(app_config, user_context=user_context)
    resolved_context, resolved_config = resolve_runtime_context()

    assert resolved_context is user_context
    assert resolved_config is app_config
    assert resolved_config.get_window_rect() == (42, 43, 800, 600)

    clear_process_app_config()


def test_get_current_runtime_uses_process_app_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from cloudscope import runtime as runtime_module
    from cloudscope.runtime import set_process_app_config

    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    set_process_app_config(app_config, user_context=user_context)

    runtime = runtime_module.get_current_runtime()

    assert runtime.app_config is app_config
    assert runtime.user_context is user_context
