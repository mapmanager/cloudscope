"""Headless tests for LoadSaveView pure helpers."""

from __future__ import annotations

from pathlib import Path

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.events.files import LoadPathKind
from cloudscope.views.load_save_view import (
    LoadSaveView,
    _path_display,
    _recent_target_exists,
)


# ---- _recent_target_exists ----


def test_recent_target_exists_file_true(tmp_path) -> None:
    """File path matching a real file should resolve to True."""
    fp = tmp_path / "a.tif"
    fp.write_text("x", encoding="utf-8")
    assert _recent_target_exists(str(fp), LoadPathKind.FILE) is True


def test_recent_target_exists_file_false_when_missing(tmp_path) -> None:
    """Missing file path should resolve to False."""
    assert _recent_target_exists(str(tmp_path / "missing.tif"), LoadPathKind.FILE) is False


def test_recent_target_exists_file_false_when_path_is_directory(tmp_path) -> None:
    """A directory should not satisfy a FILE recent."""
    assert _recent_target_exists(str(tmp_path), LoadPathKind.FILE) is False


def test_recent_target_exists_folder_true(tmp_path) -> None:
    """A real directory should satisfy a FOLDER recent."""
    folder = tmp_path / "f"
    folder.mkdir()
    assert _recent_target_exists(str(folder), LoadPathKind.FOLDER) is True


def test_recent_target_exists_folder_false_when_missing(tmp_path) -> None:
    """Missing directory should not satisfy a FOLDER recent."""
    assert _recent_target_exists(str(tmp_path / "missing"), LoadPathKind.FOLDER) is False


def test_recent_target_exists_folder_false_when_file(tmp_path) -> None:
    """A file path should not satisfy a FOLDER recent."""
    fp = tmp_path / "a.tif"
    fp.write_text("x", encoding="utf-8")
    assert _recent_target_exists(str(fp), LoadPathKind.FOLDER) is False


def test_recent_target_exists_csv_treated_as_file(tmp_path) -> None:
    """CSV path that exists should satisfy CSV recents (treated as a file)."""
    fp = tmp_path / "list.csv"
    fp.write_text("x", encoding="utf-8")
    assert _recent_target_exists(str(fp), LoadPathKind.CSV) is True


# ---- _path_display ----


def test_path_display_shortens_home_relative_path() -> None:
    """Paths under the user home should display as ``~/...``."""
    home = Path.home()
    target = home / "scratch" / "x.tif"
    out = _path_display(str(target))
    assert out.startswith("~")
    assert "scratch" in out


def test_path_display_returns_path_unchanged_outside_home() -> None:
    """Paths outside the user home should round-trip unchanged."""
    target = "/var/tmp/some/file.tif"
    assert _path_display(target) == target


# ---- _recent_item_matches_app_path ----


def _new_view(tmp_path: Path) -> LoadSaveView:
    cfg = AppConfig.load(config_path=tmp_path / "cfg.json")
    return LoadSaveView(event_bus=EventBus(), app_config=cfg, initially_visible=False)


def test_recent_item_matches_app_path_true_for_matching_last_path(tmp_path) -> None:
    """A recent item equal to ``last_path`` should match."""
    view = _new_view(tmp_path)
    view.app_config.set_last_path(str(tmp_path / "a.tif"))

    assert view._recent_item_matches_app_path(str(tmp_path / "a.tif")) is True


def test_recent_item_matches_app_path_false_for_different_path(tmp_path) -> None:
    """A different path should not match."""
    view = _new_view(tmp_path)
    view.app_config.set_last_path(str(tmp_path / "a.tif"))

    assert view._recent_item_matches_app_path(str(tmp_path / "b.tif")) is False


def test_recent_item_matches_app_path_false_when_last_path_empty(tmp_path) -> None:
    """Empty ``last_path`` should not match any recent."""
    view = _new_view(tmp_path)
    assert view._recent_item_matches_app_path(str(tmp_path / "a.tif")) is False


# ---- _resolve_initial_directory ----


def test_resolve_initial_directory_uses_last_path_dir(tmp_path) -> None:
    """When ``last_path`` is a directory, it should be returned as the initial dir."""
    folder = tmp_path / "folder"
    folder.mkdir()
    view = _new_view(tmp_path)
    view.app_config.set_last_path(str(folder))

    assert view._resolve_initial_directory() == folder


def test_resolve_initial_directory_uses_parent_of_last_file(tmp_path) -> None:
    """When ``last_path`` is a file, its parent should be returned."""
    folder = tmp_path / "folder"
    folder.mkdir()
    fp = folder / "x.tif"
    fp.write_text("x", encoding="utf-8")
    view = _new_view(tmp_path)
    view.app_config.set_last_path(str(fp))

    assert view._resolve_initial_directory() == folder


def test_resolve_initial_directory_falls_back_to_home(tmp_path) -> None:
    """When no useful ``last_path`` is set, the home directory should be returned."""
    view = _new_view(tmp_path)
    assert view._resolve_initial_directory() == Path.home()


# ---- _is_native_mode ----


def test_is_native_mode_returns_bool() -> None:
    """``_is_native_mode`` should return a boolean reflecting ``app.native`` presence."""
    assert isinstance(LoadSaveView._is_native_mode(), bool)


def test_is_native_mode_false_when_app_lacks_native(monkeypatch) -> None:
    """When ``app.native`` is None, ``_is_native_mode`` should be False."""
    from nicegui import app as nicegui_app

    monkeypatch.setattr(nicegui_app, "native", None, raising=False)
    assert LoadSaveView._is_native_mode() is False


# ---- _update_button_states with fake buttons ----


class _FakeButton:
    """Fake NiceGUI button capturing enable/disable calls."""

    def __init__(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def enable(self) -> None:
        self.enabled = True


def _fake_acq_image(is_dirty: bool):
    class _Img:
        def __init__(self) -> None:
            self.is_dirty = is_dirty

    return _Img()


def test_update_button_states_disables_save_selected_without_selection(tmp_path) -> None:
    """Save-selected should be disabled when no acq image is selected."""
    view = _new_view(tmp_path)
    view._save_selected_button = _FakeButton()
    view._save_all_button = _FakeButton()

    view._update_button_states()

    assert view._save_selected_button.enabled is False
    assert view._save_all_button.enabled is True


def test_update_button_states_disables_save_selected_when_not_dirty(tmp_path) -> None:
    """Save-selected should be disabled when the selected image is clean."""
    view = _new_view(tmp_path)
    view._save_selected_button = _FakeButton()
    view._save_all_button = _FakeButton()
    view.get_selected_acq_image = lambda: _fake_acq_image(is_dirty=False)  # type: ignore[method-assign]
    view.selected_acq_image_is_dirty = lambda: False  # type: ignore[method-assign]

    view._update_button_states()

    assert view._save_selected_button.enabled is False


def test_update_button_states_enables_save_selected_when_dirty(tmp_path) -> None:
    """Save-selected should be enabled when the selected image is dirty."""
    view = _new_view(tmp_path)
    view._save_selected_button = _FakeButton()
    view._save_all_button = _FakeButton()
    view.get_selected_acq_image = lambda: _fake_acq_image(is_dirty=True)  # type: ignore[method-assign]
    view.selected_acq_image_is_dirty = lambda: True  # type: ignore[method-assign]

    view._update_button_states()

    assert view._save_selected_button.enabled is True


def test_update_button_states_tolerates_missing_buttons(tmp_path) -> None:
    """Missing button references should not raise."""
    view = _new_view(tmp_path)
    view._save_selected_button = None
    view._save_all_button = None

    view._update_button_states()
