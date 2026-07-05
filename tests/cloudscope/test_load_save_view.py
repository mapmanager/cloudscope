"""Headless tests for LoadSaveView pure helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from cloudscope.app_config import AppConfig
from cloudscope.quota import StorageQuota
from cloudscope.event_bus import EventBus
from cloudscope.events.files import LoadPathIntent, LoadPathKind
from cloudscope.views.load_save_view import (
    LoadSaveView,
    _accepted_upload_extensions,
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


def test_pick_load_path_file_uses_acqstore_acquisition_extensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The native Load File picker should advertise every AcqImage-loadable suffix."""
    from acqstore.acq_image.supported_import_extensions import get_allowed_import_extensions
    import cloudscope.views.load_save_view as load_save_module

    view = _new_view(tmp_path)
    calls: list[dict[str, object]] = []

    async def fake_prompt_for_path(initial: Path, **kwargs) -> str:
        calls.append({'initial': initial, **kwargs})
        return '/tmp/sample.oir'

    monkeypatch.setattr(load_save_module, '_prompt_for_path', fake_prompt_for_path)

    result = asyncio.run(view._pick_load_path(LoadPathKind.FILE))

    assert result == '/tmp/sample.oir'
    assert calls == [
        {
            'initial': Path.home(),
            'dialog_type': 'file',
            'file_extensions': tuple(f'.{extension}' for extension in get_allowed_import_extensions()),
            'file_type_label': 'Acquisition files',
        }
    ]


def test_pick_load_path_csv_keeps_csv_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CSV manifests should keep their separate single-extension picker filter."""
    import cloudscope.views.load_save_view as load_save_module

    view = _new_view(tmp_path)
    calls: list[dict[str, object]] = []

    async def fake_prompt_for_path(initial: Path, **kwargs) -> str:
        calls.append({'initial': initial, **kwargs})
        return '/tmp/list.csv'

    monkeypatch.setattr(load_save_module, '_prompt_for_path', fake_prompt_for_path)

    result = asyncio.run(view._pick_load_path(LoadPathKind.CSV))

    assert result == '/tmp/list.csv'
    assert calls == [
        {
            'initial': Path.home(),
            'dialog_type': 'file',
            'file_extension': '.csv',
        }
    ]


# ---- _is_native_mode ----


def test_is_native_mode_returns_bool() -> None:
    """``_is_native_mode`` should return a boolean."""
    assert isinstance(LoadSaveView._is_native_mode(), bool)


def test_is_native_mode_false_when_no_desktop_shell(monkeypatch) -> None:
    """Without Option C or NiceGUI native proxy, desktop pickers are disabled."""
    from nicegui import app as nicegui_app

    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None)
    monkeypatch.setattr(nicegui_app, 'native', SimpleNamespace(main_window=None), raising=False)
    assert LoadSaveView._is_native_mode() is False


def test_is_native_mode_true_for_option_c(monkeypatch) -> None:
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: object())
    assert LoadSaveView._is_native_mode() is True


def test_is_native_mode_false_when_app_lacks_native(monkeypatch) -> None:
    """When ``app.native`` is None, ``_is_native_mode`` should be False."""
    from nicegui import app as nicegui_app

    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None)
    monkeypatch.setattr(nicegui_app, 'native', None, raising=False)
    assert LoadSaveView._is_native_mode() is False


def test_build_upload_control_skipped_in_native_mode(monkeypatch, tmp_path) -> None:
    """Native runs should not build the browser upload control."""
    from nicegui import app as nicegui_app

    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None)
    monkeypatch.setattr(nicegui_app, 'native', SimpleNamespace(main_window=object()), raising=False)
    view = _new_view(tmp_path)

    view._build_upload_control()

    assert view._upload_widget is None


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


def test_update_button_states_disables_load_buttons_when_not_native(tmp_path, monkeypatch) -> None:
    """Load File/Folder should be disabled when native pickers are unavailable."""
    monkeypatch.setattr(LoadSaveView, '_is_native_mode', staticmethod(lambda: False))
    view = _new_view(tmp_path)
    view._load_file_button = _FakeButton()
    view._load_folder_button = _FakeButton()
    view._save_selected_button = _FakeButton()
    view._save_all_button = _FakeButton()

    view._update_button_states()

    assert view._load_file_button.enabled is False
    assert view._load_folder_button.enabled is False


def test_update_button_states_enables_load_buttons_in_native_mode(tmp_path, monkeypatch) -> None:
    """Load File/Folder should stay enabled when native pickers are available."""
    monkeypatch.setattr(LoadSaveView, '_is_native_mode', staticmethod(lambda: True))
    view = _new_view(tmp_path)
    view._load_file_button = _FakeButton()
    view._load_folder_button = _FakeButton()
    view._load_file_button.disable()
    view._load_folder_button.disable()

    view._update_button_states()

    assert view._load_file_button.enabled is True
    assert view._load_folder_button.enabled is True


def test_update_button_states_keeps_load_buttons_disabled_after_save_refresh(
    tmp_path,
    monkeypatch,
) -> None:
    """Busy/selection refresh must not re-enable load buttons on web/server runs."""
    monkeypatch.setattr(LoadSaveView, '_is_native_mode', staticmethod(lambda: False))
    view = _new_view(tmp_path)
    view._load_file_button = _FakeButton()
    view._load_folder_button = _FakeButton()
    view._save_selected_button = _FakeButton()
    view._save_all_button = _FakeButton()
    view.get_selected_acq_image = lambda: _fake_acq_image(is_dirty=True)  # type: ignore[method-assign]
    view.selected_acq_image_is_dirty = lambda: True  # type: ignore[method-assign]

    view._update_button_states()

    assert view._load_file_button.enabled is False
    assert view._load_folder_button.enabled is False
    assert view._save_selected_button.enabled is True


def test_local_path_pickers_enabled_matches_native_mode(monkeypatch) -> None:
    """``_local_path_pickers_enabled`` should mirror ``_is_native_mode``."""
    monkeypatch.setattr(LoadSaveView, '_is_native_mode', staticmethod(lambda: True))
    assert LoadSaveView._local_path_pickers_enabled() is True
    monkeypatch.setattr(LoadSaveView, '_is_native_mode', staticmethod(lambda: False))
    assert LoadSaveView._local_path_pickers_enabled() is False


def test_load_sample_data_clicked_publishes_sample_intent(tmp_path) -> None:
    from acqstore.sample_data import VELOCITY_SAMPLE_DATA
    from cloudscope.events.files import LoadSampleDataIntent

    view = _new_view(tmp_path)
    events: list[LoadSampleDataIntent] = []
    view.event_bus.subscribe(LoadSampleDataIntent, events.append)

    view._on_load_sample_data_clicked(VELOCITY_SAMPLE_DATA)

    assert events == [LoadSampleDataIntent(name=VELOCITY_SAMPLE_DATA)]


def _server_demo_view(tmp_path: Path) -> LoadSaveView:
    from cloudscope.user_context import resolve_user_context

    context = resolve_user_context(remote=True, native=False, demo_session_id='demo-manning')
    context = context.__class__(
        kind=context.kind,
        user_id=context.user_id,
        config_path=tmp_path / 'demo' / 'app_config.json',
        data_dir=tmp_path / 'demo',
        upload_dir=tmp_path / 'demo' / 'uploads',
        sample_data_dir=tmp_path / 'shared' / 'sample-data',
        cache_dir=tmp_path / 'demo' / 'cache',
        quota=context.quota,
        last_used_path=tmp_path / 'demo' / '.last_used',
        persistent=False,
    )
    cfg = AppConfig.ephemeral(config_path=context.config_path)
    return LoadSaveView(event_bus=EventBus(), app_config=cfg, user_context=context, initially_visible=False)


def test_manning_preset_load_path_hidden_for_local_desktop(tmp_path: Path) -> None:
    from cloudscope.user_context import resolve_user_context

    context = resolve_user_context(remote=False, native=True)
    view = LoadSaveView(
        event_bus=EventBus(),
        app_config=AppConfig.ephemeral(config_path=tmp_path / 'cfg.json'),
        user_context=context,
        initially_visible=False,
    )
    assert view._manning_preset_load_path() is None


def test_manning_preset_load_path_uses_env_on_server(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cloudscope.preset_data import PRESET_MANNING_ENV

    preset = tmp_path / 'manning'
    preset.mkdir()
    monkeypatch.setenv(PRESET_MANNING_ENV, str(preset))
    view = _server_demo_view(tmp_path)
    assert view._manning_preset_load_path() == preset


def test_on_load_manning_preset_clicked_publishes_folder_intent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cloudscope.preset_data import PRESET_MANNING_ENV

    preset = tmp_path / 'manning'
    preset.mkdir()
    (preset / 'sample.tif').write_bytes(b'x')
    monkeypatch.setenv(PRESET_MANNING_ENV, str(preset))
    view = _server_demo_view(tmp_path)
    events: list[LoadPathIntent] = []
    view.event_bus.subscribe(LoadPathIntent, events.append)

    view._on_load_manning_preset_clicked()

    assert events == [
        LoadPathIntent(path=str(preset), kind=LoadPathKind.FOLDER, from_recent=False),
    ]


def test_on_load_manning_preset_clicked_noop_when_preset_not_loadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cloudscope.preset_data import PRESET_MANNING_ENV

    preset = tmp_path / 'manning'
    preset.mkdir()
    monkeypatch.setenv(PRESET_MANNING_ENV, str(preset))
    view = _server_demo_view(tmp_path)
    events: list[LoadPathIntent] = []
    view.event_bus.subscribe(LoadPathIntent, events.append)

    view._on_load_manning_preset_clicked()

    assert events == []


# ---- upload helpers ----


def test_accepted_upload_extensions_includes_default_acquisition_suffixes() -> None:
    """The accept string should advertise the AcqStore default acquisition suffixes."""
    accepted = _accepted_upload_extensions()
    parts = set(accepted.split(','))
    assert {'.tif', '.oir', '.czi'}.issubset(parts)


def test_handle_upload_paths_publishes_load_intent_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful upload persistence should yield a load intent and a positive notice."""
    view = _new_view(tmp_path)

    src = tmp_path / 'source.tmp'
    src.write_bytes(b'data')
    target_upload_dir = tmp_path / 'uploads'

    import cloudscope.views.load_save_view as load_save_module

    def fake_store(source_path: Path, *, original_filename: str, upload_dir=None) -> Path:
        from acqstore.upload_store import store_uploaded_file

        return store_uploaded_file(
            source_path,
            original_filename=original_filename,
            upload_dir=upload_dir or target_upload_dir,
        )

    monkeypatch.setattr(load_save_module, 'store_uploaded_file', fake_store)

    outcome = view._handle_upload_paths(source_path=src, original_filename='sample.oir')

    assert outcome.intent == LoadPathIntent(
        path=str(target_upload_dir / 'sample.oir'),
        kind=LoadPathKind.FILE,
        from_recent=False,
    )
    assert outcome.notify is not None
    assert outcome.notify.type == 'positive'
    assert (target_upload_dir / 'sample.oir').read_bytes() == b'data'


def test_handle_upload_paths_warns_on_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An existing upload should yield no intent and a warning notice."""
    view = _new_view(tmp_path)

    src = tmp_path / 'source.tmp'
    src.write_bytes(b'data')
    target_upload_dir = tmp_path / 'uploads'
    target_upload_dir.mkdir()
    (target_upload_dir / 'sample.oir').write_bytes(b'existing')

    import cloudscope.views.load_save_view as load_save_module

    def fake_store(source_path: Path, *, original_filename: str, upload_dir=None) -> Path:
        from acqstore.upload_store import store_uploaded_file

        return store_uploaded_file(
            source_path,
            original_filename=original_filename,
            upload_dir=upload_dir or target_upload_dir,
        )

    monkeypatch.setattr(load_save_module, 'store_uploaded_file', fake_store)

    outcome = view._handle_upload_paths(source_path=src, original_filename='sample.oir')

    assert outcome.intent is None
    assert outcome.notify is not None
    assert outcome.notify.type == 'warning'
    assert 'already exists' in outcome.notify.message


def test_handle_upload_paths_warns_on_unsupported_extension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported extensions should be rejected at the view layer with a warning."""
    view = _new_view(tmp_path)

    src = tmp_path / 'source.tmp'
    src.write_bytes(b'data')
    target_upload_dir = tmp_path / 'uploads'

    import cloudscope.views.load_save_view as load_save_module

    def fake_store(source_path: Path, *, original_filename: str, upload_dir=None) -> Path:
        from acqstore.upload_store import store_uploaded_file

        return store_uploaded_file(
            source_path,
            original_filename=original_filename,
            upload_dir=upload_dir or target_upload_dir,
        )

    monkeypatch.setattr(load_save_module, 'store_uploaded_file', fake_store)

    outcome = view._handle_upload_paths(source_path=src, original_filename='sample.png')

    assert outcome.intent is None
    assert outcome.notify is not None
    assert outcome.notify.type == 'warning'


def test_handle_upload_paths_uses_user_context_upload_dir(tmp_path: Path) -> None:
    """Upload persistence should use the per-user upload directory when supplied."""
    from cloudscope.user_context import resolve_user_context

    context = resolve_user_context(remote=True, native=False, demo_session_id='demo-upload')
    context = context.__class__(
        kind=context.kind,
        user_id=context.user_id,
        config_path=tmp_path / 'demo' / 'app_config.json',
        data_dir=tmp_path / 'demo',
        upload_dir=tmp_path / 'demo' / 'uploads',
        sample_data_dir=tmp_path / 'shared' / 'sample-data',
        cache_dir=tmp_path / 'demo' / 'cache',
        quota=StorageQuota(quota_bytes=1024),
        last_used_path=tmp_path / 'demo' / '.last_used',
        persistent=False,
    )
    cfg = AppConfig.ephemeral(config_path=context.config_path)
    view = LoadSaveView(event_bus=EventBus(), app_config=cfg, user_context=context, initially_visible=False)
    src = tmp_path / 'source.tmp'
    src.write_bytes(b'data')

    outcome = view._handle_upload_paths(source_path=src, original_filename='sample.oir')

    assert outcome.intent == LoadPathIntent(
        path=str(context.upload_dir / 'sample.oir'),
        kind=LoadPathKind.FILE,
        from_recent=False,
    )
    assert (context.upload_dir / 'sample.oir').read_bytes() == b'data'


def test_handle_upload_paths_rejects_user_context_quota(tmp_path: Path) -> None:
    """Uploads that exceed the per-context quota should be rejected before copying."""
    from cloudscope.user_context import resolve_user_context

    context = resolve_user_context(remote=True, native=False, demo_session_id='demo-quota')
    context = context.__class__(
        kind=context.kind,
        user_id=context.user_id,
        config_path=tmp_path / 'demo' / 'app_config.json',
        data_dir=tmp_path / 'demo',
        upload_dir=tmp_path / 'demo' / 'uploads',
        sample_data_dir=tmp_path / 'shared' / 'sample-data',
        cache_dir=tmp_path / 'demo' / 'cache',
        quota=StorageQuota(quota_bytes=1),
        last_used_path=tmp_path / 'demo' / '.last_used',
        persistent=False,
    )
    cfg = AppConfig.ephemeral(config_path=context.config_path)
    view = LoadSaveView(event_bus=EventBus(), app_config=cfg, user_context=context, initially_visible=False)
    src = tmp_path / 'source.tmp'
    src.write_bytes(b'data')

    outcome = view._handle_upload_paths(source_path=src, original_filename='sample.oir')

    assert outcome.intent is None
    assert outcome.notify is not None
    assert outcome.notify.type == 'warning'
    assert 'quota' in outcome.notify.message.lower()
    assert not (context.upload_dir / 'sample.oir').exists()


def test_handle_upload_paths_rejects_user_context_max_upload(tmp_path: Path) -> None:
    """Uploads larger than the per-context file limit should be rejected before copying."""
    from cloudscope.user_context import resolve_user_context

    context = resolve_user_context(remote=True, native=False, demo_session_id='demo-max-upload')
    context = context.__class__(
        kind=context.kind,
        user_id=context.user_id,
        config_path=tmp_path / 'demo' / 'app_config.json',
        data_dir=tmp_path / 'demo',
        upload_dir=tmp_path / 'demo' / 'uploads',
        sample_data_dir=tmp_path / 'shared' / 'sample-data',
        cache_dir=tmp_path / 'demo' / 'cache',
        quota=StorageQuota(quota_bytes=1024, max_upload_bytes=1),
        last_used_path=tmp_path / 'demo' / '.last_used',
        persistent=False,
    )
    cfg = AppConfig.ephemeral(config_path=context.config_path)
    view = LoadSaveView(event_bus=EventBus(), app_config=cfg, user_context=context, initially_visible=False)
    src = tmp_path / 'source.tmp'
    src.write_bytes(b'data')

    outcome = view._handle_upload_paths(source_path=src, original_filename='sample.oir')

    assert outcome.intent is None
    assert outcome.notify is not None
    assert outcome.notify.type == 'warning'
    assert 'larger' in outcome.notify.message.lower()
    assert not (context.upload_dir / 'sample.oir').exists()
