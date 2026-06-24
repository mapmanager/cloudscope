"""Tests for Option C desktop quit flow and native quit dialog dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cloudscope.app_config import AppConfig
from cloudscope.desktop.quit_dialog import QuitChoice, ask_quit_with_unsaved_changes
from cloudscope.desktop.quit_flow import handle_main_window_closing
from cloudscope.desktop.save_on_quit import has_dirty_files, save_all_dirty_files_sync
from cloudscope.window_geometry import WindowGeometryTracker


class _FakeWindow:
    def __init__(self, *, x: int = 10, y: int = 20, width: int = 800, height: int = 600) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height


def _tracker(app_config: AppConfig, window: _FakeWindow) -> WindowGeometryTracker:
    return WindowGeometryTracker(
        window,
        app_config.get_window_rect,
        app_config.set_window_rect,
        save=app_config.save,
    )


def test_handle_main_window_closing_clean_quit_syncs_and_persists(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    window = _FakeWindow(x=30, y=40, width=900, height=700)
    tracker = _tracker(app_config, window)

    allowed = handle_main_window_closing(
        tracker,
        has_dirty=lambda: False,
    )

    assert allowed is True
    assert app_config.get_window_rect() == (30, 40, 900, 700)


def test_handle_main_window_closing_cancel_vetoes_close(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    tracker = _tracker(app_config, _FakeWindow())
    save_dirty = MagicMock()

    allowed = handle_main_window_closing(
        tracker,
        has_dirty=lambda: True,
        ask_quit=lambda: QuitChoice.CANCEL,
        save_dirty=save_dirty,
    )

    assert allowed is False
    save_dirty.assert_not_called()


def test_handle_main_window_closing_save_calls_sync_save_and_persist(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    window = _FakeWindow(x=5, y=6, width=700, height=500)
    tracker = _tracker(app_config, window)
    save_dirty = MagicMock()

    allowed = handle_main_window_closing(
        tracker,
        has_dirty=lambda: True,
        ask_quit=lambda: QuitChoice.SAVE,
        save_dirty=save_dirty,
    )

    assert allowed is True
    save_dirty.assert_called_once()
    assert app_config.get_window_rect() == (5, 6, 700, 500)


def test_handle_main_window_closing_discard_skips_save_dirty(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    tracker = _tracker(app_config, _FakeWindow(x=1, y=2, width=300, height=400))
    save_dirty = MagicMock()

    allowed = handle_main_window_closing(
        tracker,
        has_dirty=lambda: True,
        ask_quit=lambda: QuitChoice.DISCARD,
        save_dirty=save_dirty,
    )

    assert allowed is True
    save_dirty.assert_not_called()
    assert app_config.get_window_rect() == (1, 2, 300, 400)


def test_ask_quit_with_unsaved_changes_uses_injected_backend() -> None:
    def _backend(title: str, message: str) -> QuitChoice:
        assert title == 'Title'
        assert message == 'Body'
        return QuitChoice.DISCARD

    choice = ask_quit_with_unsaved_changes(
        title='Title',
        message='Body',
        dialog_fn=_backend,
    )
    assert choice is QuitChoice.DISCARD


def test_save_all_dirty_files_sync_saves_each_dirty_file() -> None:
    dirty_a = MagicMock()
    dirty_a.is_dirty = True
    dirty_b = MagicMock()
    dirty_b.is_dirty = True
    clean = MagicMock()
    clean.is_dirty = False
    acq_list = MagicMock()
    acq_list.get_dirty_files.return_value = (dirty_a, dirty_b)

    runtime = MagicMock()
    runtime.home_page_controller.state.acq_image_list = acq_list

    with patch('cloudscope.desktop.save_on_quit.get_current_runtime', return_value=runtime):
        save_all_dirty_files_sync()

    dirty_a.save.assert_called_once()
    dirty_b.save.assert_called_once()
    clean.save.assert_not_called()


def test_has_dirty_files_false_when_no_list() -> None:
    runtime = MagicMock()
    runtime.home_page_controller.state.acq_image_list = None

    with patch('cloudscope.desktop.save_on_quit.get_current_runtime', return_value=runtime):
        assert has_dirty_files() is False


def test_has_dirty_files_uses_acq_image_list_api() -> None:
    acq_list = MagicMock()
    acq_list.has_dirty_files.return_value = True
    runtime = MagicMock()
    runtime.home_page_controller.state.acq_image_list = acq_list

    with patch('cloudscope.desktop.save_on_quit.get_current_runtime', return_value=runtime):
        assert has_dirty_files() is True

    acq_list.has_dirty_files.assert_called_once()


def test_has_dirty_files_uses_home_page_controller_on_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: quit flow must use ``home_page_controller``, not ``home_controller``."""
    from cloudscope.runtime import clear_process_app_config, set_process_app_config, _build_runtime
    from tests.cloudscope.test_runtime import _local_context

    user_context = _local_context()
    app_config = AppConfig.ephemeral(config_path=user_context.config_path)
    runtime = _build_runtime(user_context, app_config)
    acq_list = MagicMock()
    acq_list.has_dirty_files.return_value = True
    runtime.home_page_controller.state.acq_image_list = acq_list

    set_process_app_config(app_config, user_context=user_context)
    monkeypatch.setattr(
        'cloudscope.desktop.save_on_quit.get_current_runtime',
        lambda: runtime,
    )
    try:
        assert has_dirty_files() is True
    finally:
        clear_process_app_config()


@pytest.mark.parametrize(
    ('platform', 'expected'),
    [
        ('darwin', QuitChoice.SAVE),
        ('win32', QuitChoice.DISCARD),
        ('linux', QuitChoice.CANCEL),
    ],
)
def test_default_quit_dialog_dispatches_by_platform(platform: str, expected: QuitChoice) -> None:
    from cloudscope.desktop import quit_dialog as quit_dialog_module

    with (
        patch.object(quit_dialog_module, 'sys') as mock_sys,
        patch.object(quit_dialog_module, '_ask_quit_darwin', return_value=QuitChoice.SAVE) as darwin,
        patch.object(quit_dialog_module, '_ask_quit_win32', return_value=QuitChoice.DISCARD) as win32,
    ):
        mock_sys.platform = platform
        choice = quit_dialog_module._default_quit_dialog('Title', 'Message')

    assert choice is expected
    if platform == 'darwin':
        darwin.assert_called_once()
    elif platform == 'win32':
        win32.assert_called_once()
