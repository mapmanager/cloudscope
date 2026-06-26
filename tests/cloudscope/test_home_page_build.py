"""Smoke tests for CloudScope home page route wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cloudscope.app_config import AppConfig
from cloudscope.runtime import _build_runtime, reset_runtime_registry_for_tests
from cloudscope.user_context import UserContext, UserContextKind


@pytest.fixture(autouse=True)
def _clear_runtime_registry() -> None:
    reset_runtime_registry_for_tests()
    yield
    reset_runtime_registry_for_tests()


def test_home_page_wires_runtime_into_home_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """home_page() should initialize runtime once and pass shared controllers to HomePage."""
    user_context = UserContext(
        kind=UserContextKind.LOCAL_OS_USER,
        user_id='local',
        config_path=AppConfig.default_config_path(),
        data_dir=AppConfig.default_config_path().parent,
        upload_dir=AppConfig.default_config_path().parent / 'uploads',
        sample_data_dir=AppConfig.default_config_path().parent / 'sample-data',
        cache_dir=AppConfig.default_config_path().parent / 'cache',
    )
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    shared_runtime = _build_runtime(user_context, app_config)
    init_calls: list[bool] = []

    class _RecordingRuntime:
        def __init__(self, runtime) -> None:
            self._runtime = runtime

        def initialize_once(self) -> None:
            init_calls.append(True)
            self._runtime.initialize_once()

        def __getattr__(self, name: str):
            return getattr(self._runtime, name)

    recording_runtime = _RecordingRuntime(shared_runtime)
    monkeypatch.setattr(
        'cloudscope.pages.home_page.get_current_runtime',
        lambda: recording_runtime,
    )

    built: list[object] = []
    captured_kwargs: list[dict[str, object]] = []

    class FakeHomePage:
        def __init__(self, **kwargs) -> None:
            captured_kwargs.append(kwargs)

        def build(self) -> None:
            built.append(self)

    monkeypatch.setattr('cloudscope.pages.home_page.HomePage', FakeHomePage)

    from cloudscope.pages.home_page import home_page

    home_page()

    assert init_calls == [True]
    assert built
    assert captured_kwargs
    kwargs = captured_kwargs[0]
    assert kwargs['controller'] is shared_runtime.home_page_controller
    assert kwargs['load_save_controller'] is shared_runtime.load_save_controller
    assert kwargs['event_bus'] is shared_runtime.event_bus
    assert kwargs['app_config'] is shared_runtime.app_config
    assert kwargs['velocity_pool_controller'] is shared_runtime.velocity_pool_controller
    assert kwargs['task_runner'] is shared_runtime.task_runner


def test_home_page_install_shutdown_handlers_registers_config_save(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native shutdown should persist app config through app.on_shutdown."""
    from cloudscope.pages.home_page import HomePage

    cfg_path = tmp_path / 'app_config.json'
    app_config = AppConfig(path=cfg_path, persistent=True)
    runtime = _build_runtime(
        UserContext(
            kind=UserContextKind.LOCAL_OS_USER,
            user_id='local',
            config_path=cfg_path,
            data_dir=tmp_path,
            upload_dir=tmp_path / 'uploads',
            sample_data_dir=tmp_path / 'sample-data',
            cache_dir=tmp_path / 'cache',
        ),
        app_config,
    )
    shutdown_handlers: list[object] = []

    class FakeNative:
        def on(self, _event: str, _handler) -> None:
            return None

    class FakeApp:
        native = FakeNative()

        @staticmethod
        def on_shutdown(handler) -> None:
            shutdown_handlers.append(handler)

    monkeypatch.setattr('cloudscope.pages.home_page.app', FakeApp())
    page = HomePage(
        controller=runtime.home_page_controller,
        load_save_controller=runtime.load_save_controller,
        event_bus=runtime.event_bus,
        app_config=app_config,
        user_context=runtime.user_context,
        analysis_controller=runtime.analysis_controller,
        roi_controller=runtime.roi_controller,
        event_analysis_controller=runtime.event_analysis_controller,
        velocity_pool_controller=runtime.velocity_pool_controller,
        task_runner=runtime.task_runner,
    )

    page._install_shutdown_handlers()

    assert len(shutdown_handlers) == 1
    app_config.data.text_size = 'large'
    import asyncio

    asyncio.run(shutdown_handlers[0]())
    reloaded = AppConfig.load(config_path=cfg_path)
    assert reloaded.data.text_size == 'large'
