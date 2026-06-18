"""Tests for the standalone pool page route."""

from __future__ import annotations

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


def test_pool_page_module_imports() -> None:
    from cloudscope.pages import pool_page  # noqa: F401

    assert callable(pool_page.pool_page)


def test_pool_page_uses_shared_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    from cloudscope import runtime as runtime_module

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
    monkeypatch.setattr('cloudscope.pages.pool_page.get_current_runtime', lambda: shared_runtime)

    calls: list[object] = []

    class FakeClient:
        def on_disconnect(self, handler) -> None:
            calls.append(handler)

    class FakeContext:
        client = FakeClient()

    monkeypatch.setattr('cloudscope.pages.pool_page.ui.context', FakeContext())
    monkeypatch.setattr('cloudscope.pages.pool_page.setUpGuiDefaults', lambda *_args, **_kwargs: None)
    monkeypatch.setattr('cloudscope.pages.pool_page.build_main_header', lambda **_kwargs: None)
    monkeypatch.setattr('cloudscope.pages.pool_page.ui.page_title', lambda *_args, **_kwargs: None)

    built: list[object] = []
    footer_built: list[object] = []

    class FakeFooterView:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def build(self) -> None:
            footer_built.append(self)

        def on_hide(self) -> None:
            return None

    class FakePoolView:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def build(self) -> None:
            built.append(self)

        def on_hide(self) -> None:
            return None

    monkeypatch.setattr('cloudscope.pages.pool_page.VelocityPoolView', FakePoolView)
    monkeypatch.setattr('cloudscope.pages.pool_page.FooterView', FakeFooterView)
    monkeypatch.setattr(
        'cloudscope.pages.pool_page.ui.column',
        lambda *_args, **_kwargs: MagicMock(__enter__=lambda s: s, __exit__=lambda *a: None),
    )

    from cloudscope.pages.pool_page import pool_page

    pool_page()

    assert built
    assert footer_built
    assert footer_built[0].kwargs['show_status'] is False
    assert built[0].kwargs['event_bus'] is shared_runtime.event_bus
    assert built[0].kwargs['app_state'] is shared_runtime.app_state
