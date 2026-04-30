"""Load/save toolbar view for CloudScope."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path

from nicegui import app, ui

from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import (
    AppStatusChanged,
    ClearRecentPathsIntent,
    FileSelectionChanged,
    LoadPathKind,
    LoadPathIntent,
    RecentPathsChanged,
    RemoveRecentPathIntent,
    SaveAllIntent,
    SaveSelectedIntent,
    StatusLevel,
    StatusSource,
    TaskProgressChanged,
)
from cloudscope.gui._py_web_view import _prompt_for_path, _prompt_for_save_path
from cloudscope.gui.app_config import AppConfig
from cloudscope.core.utils.logging import get_logger

logger = get_logger(__name__)


def _recent_target_exists(path: str, kind: LoadPathKind) -> bool:
    """Return whether ``path`` exists on disk in the shape expected for ``kind``."""
    p = Path(path).expanduser()
    try:
        resolved = p.resolve(strict=False)
    except OSError:
        resolved = p
    if kind == LoadPathKind.FOLDER:
        return resolved.is_dir()
    return resolved.is_file()


def _path_display(path: str) -> str:
    """Shorten absolute paths under the user home to ``~/…`` for menu labels."""
    try:
        p = Path(path).expanduser()
        home = Path.home()
        rel = p.resolve(strict=False).relative_to(home.resolve(strict=False))
        return str(Path('~') / rel)
    except (ValueError, OSError, RuntimeError):
        return path


@dataclass
class LoadSaveView:
    """Toolbar that emits load/save intents and renders recents/progress UI."""

    event_bus: EventBus
    app_config: AppConfig

    def __post_init__(self) -> None:
        # self._path_input: ui.input | None = None
        self._save_selected_button: ui.button | None = None
        self._save_all_button: ui.button | None = None
        self._current_file_id: str | None = None
        self._current_file_dirty: bool = False
        self._progress_dialog: ui.dialog | None = None
        self._progress_bar: ui.linear_progress | None = None
        self._progress_label: ui.label | None = None
        self._progress_message: ui.label | None = None
        self._client = None
        self._history_menu_container: ui.element | None = None
        self._history_button: ui.button | None = None
        self._recent_menu: ui.menu | None = None

        self.event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self.event_bus.subscribe(RecentPathsChanged, self._on_recent_paths_changed)
        self.event_bus.subscribe(TaskProgressChanged, self._on_task_progress_changed)
        self.event_bus.subscribe(AppStatusChanged, self._on_status_changed)

    def build(self) -> None:
        """Build toolbar UI."""
        self._client = ui.context.client
        with ui.row().classes('w-full items-center gap-2'):

            # self._path_input = ui.input(
            #     label='Path',
            #     placeholder='Enter file/folder/csv path then click load button',
            # ).classes('grow')

            # History control: button + menu as siblings in a wrapper (KymFlow-style) so
            # the menu can be deleted/rebuilt when RecentPathsChanged fires.
            with ui.element('div').classes('inline-flex items-center shrink-0') as hist_wrap:
                self._history_menu_container = hist_wrap
                self._history_button = ui.button(
                    icon='menu',
                    on_click=self._open_recent_menu,
                ).props('flat')
                self._build_recent_menu()

            ui.button('Load File', on_click=lambda: self._on_load_clicked(LoadPathKind.FILE))
            ui.button('Load Folder', on_click=lambda: self._on_load_clicked(LoadPathKind.FOLDER))
            ui.button('Load CSV', on_click=lambda: self._on_load_clicked(LoadPathKind.CSV))

            self._save_selected_button = ui.button(
                'Save Selected',
                on_click=self._on_save_selected_clicked,
            )
            self._save_all_button = ui.button(
                'Save All',
                on_click=self._on_save_all_clicked,
            )

        self._build_progress_dialog()
        self._update_button_states()

    def _build_progress_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card().classes('w-[460px]'):
            self._progress_label = ui.label('Task').classes('text-lg font-semibold')
            self._progress_message = ui.label('').classes('text-sm text-gray-600')
            self._progress_bar = ui.linear_progress(value=0.0).classes('w-full')
        self._progress_dialog = dialog

    def _open_recent_menu(self) -> None:
        """Open the recent-paths menu (used by the history button)."""
        if self._recent_menu is not None:
            self._recent_menu.open()

    def _build_recent_menu(self) -> None:
        """Create ``self._recent_menu`` as a sibling of the history button.

        Call only while the NiceGUI slot is the history wrapper (see ``build()``).
        """
        if self._history_menu_container is None:
            return
        with ui.menu() as menu:
            self._recent_menu = menu
            self._fill_recent_menu(menu)
        self._update_history_button_enabled()

    def _fill_recent_menu(self, menu: ui.menu) -> None:
        recent_folders = self.app_config.get_recent_folders()
        recent_files = self.app_config.get_recent_files()
        logger.info('recent_folders=%s recent_files=%s', recent_folders, recent_files)
        with menu:
            for item in recent_folders:
                label = f'{_path_display(item)}'
                ui.menu_item(label, lambda p=item: self._load_recent(p, LoadPathKind.FOLDER))
            if recent_folders and recent_files:
                ui.separator()
            for item in recent_files:
                kind = LoadPathKind.CSV if item.lower().endswith('.csv') else LoadPathKind.FILE
                label = f'{_path_display(item)}'
                ui.menu_item(label, lambda p=item, k=kind: self._load_recent(p, k))
            if recent_folders or recent_files:
                ui.separator()
                ui.menu_item('Clear recents', lambda: self.event_bus.publish(ClearRecentPathsIntent()))

    def _rebuild_history_menu_impl(self) -> None:
        """Close/delete the old menu and rebuild from ``app_config`` (KymFlow-style)."""
        if self._history_menu_container is None or self._history_button is None:
            return
        try:
            if self._recent_menu is not None:
                self._recent_menu.close()
        except Exception:
            logger.debug('recent menu close failed', exc_info=True)
        try:
            if self._recent_menu is not None:
                self._recent_menu.delete()
        except Exception:
            logger.debug('recent menu delete failed', exc_info=True)
        self._recent_menu = None
        with self._history_menu_container:
            with ui.menu() as menu:
                self._recent_menu = menu
                self._fill_recent_menu(menu)
        self._update_history_button_enabled()

    def _update_history_button_enabled(self) -> None:
        if self._history_button is None:
            return
        has_any = bool(self.app_config.get_recent_folders() or self.app_config.get_recent_files())
        if has_any:
            self._history_button.enable()
        else:
            self._history_button.disable()

    # def _emit_load(self, kind: LoadPathKind) -> None:
    #     if self._path_input is None:
    #         return
    #     path = str(self._path_input.value or '').strip()
    #     if not path:
    #         ui.notify('Enter a path before loading', type='warning')
    #         return
    #     self.event_bus.publish(LoadPathIntent(path=path, kind=kind))

    async def _on_load_clicked(self, kind: LoadPathKind) -> None:
        """Open native picker in native mode, else use text input path."""
        if self._is_native_mode():
            selected = await self._pick_load_path(kind)
            if selected is None:
                return
            # if self._path_input is not None:
            #     self._path_input.value = selected
            self.event_bus.publish(LoadPathIntent(path=selected, kind=kind, from_recent=False))
            return
        # self._emit_load(kind)

    async def _pick_load_path(self, kind: LoadPathKind) -> str | None:
        """Open the correct native picker for requested load kind."""
        initial = self._resolve_initial_directory()
        if kind == LoadPathKind.FOLDER:
            return await _prompt_for_path(initial, dialog_type='folder')
        if kind == LoadPathKind.CSV:
            return await _prompt_for_path(initial, dialog_type='file', file_extension='.csv')
        return await _prompt_for_path(initial, dialog_type='file', file_extension='.tif')

    async def _on_save_selected_clicked(self) -> None:
        """Open save-path picker in native mode, then emit save-selected intent."""
        if self._is_native_mode():
            selected = await _prompt_for_save_path(
                self._resolve_initial_directory(),
                suggested_filename='cloudscope_selected_save.csv',
                file_extension='.csv',
            )
            if selected is None:
                return
            self.event_bus.publish(
                AppStatusChanged(
                    level=StatusLevel.INFO,
                    source=StatusSource.SAVE,
                    message=f'Save destination selected: {selected}',
                )
            )
        self.event_bus.publish(SaveSelectedIntent())

    async def _on_save_all_clicked(self) -> None:
        """Open save-path picker in native mode, then emit save-all intent."""
        if self._is_native_mode():
            selected = await _prompt_for_save_path(
                self._resolve_initial_directory(),
                suggested_filename='cloudscope_save_all.csv',
                file_extension='.csv',
            )
            if selected is None:
                return
            self.event_bus.publish(
                AppStatusChanged(
                    level=StatusLevel.INFO,
                    source=StatusSource.SAVE,
                    message=f'Save destination selected: {selected}',
                )
            )
        self.event_bus.publish(SaveAllIntent())

    def _load_recent(self, path: str, kind: LoadPathKind) -> None:
        if not _recent_target_exists(path, kind):
            self._show_missing_recent_path_dialog(path)
            self.event_bus.publish(RemoveRecentPathIntent(path=path, kind=kind))
            return
        self.event_bus.publish(LoadPathIntent(path=path, kind=kind, from_recent=True))

    def _show_missing_recent_path_dialog(self, path: str) -> None:
        """Show a KymFlow-style dialog when a recent menu path no longer exists."""
        display = _path_display(path)

        def open_dialog() -> None:
            with ui.dialog() as dialog, ui.card().classes('w-[520px]'):
                ui.label('Item does not exist').classes('text-lg font-semibold')
                ui.label(display).classes('text-sm break-all text-gray-700')
                if display != path:
                    ui.label(path).classes('text-xs break-all text-gray-500')
                with ui.row().classes('justify-end w-full'):
                    ui.button('OK', on_click=dialog.close)
            dialog.open()

        self._run_ui(open_dialog)

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        def apply() -> None:
            self._current_file_id = event.file_id
            self._current_file_dirty = bool(event.acq_image is not None and event.acq_image.is_dirty)
            self._update_button_states()

        self._run_ui(apply)

    def _on_recent_paths_changed(self, _event: RecentPathsChanged) -> None:
        def apply() -> None:
            self._rebuild_history_menu_impl()

        self._run_ui(apply)

    def _on_status_changed(self, event: AppStatusChanged) -> None:
        self._notify_status(event.message, event.level.value)

    def _on_task_progress_changed(self, event: TaskProgressChanged) -> None:
        def apply() -> None:
            if (
                self._progress_dialog is None
                or self._progress_bar is None
                or self._progress_label is None
                or self._progress_message is None
            ):
                return
            self._progress_label.text = event.task_label
            self._progress_message.text = event.message
            denom = 1 if event.total <= 0 else event.total
            self._progress_bar.value = min(1.0, max(0.0, event.current / denom))
            if event.status.value in {'queued', 'running'}:
                self._progress_dialog.open()
            else:
                self._progress_dialog.close()
            self._update_button_states()

        self._run_ui(apply)

    def _update_button_states(self) -> None:
        if self._save_selected_button is not None:
            if self._current_file_id is None or not self._current_file_dirty:
                self._save_selected_button.disable()
            else:
                self._save_selected_button.enable()
        if self._save_all_button is not None:
            self._save_all_button.enable()

    @staticmethod
    def _is_native_mode() -> bool:
        """Return whether NiceGUI native runtime is available."""
        return getattr(app, 'native', None) is not None

    def _resolve_initial_directory(self) -> Path:
        """Resolve best-effort initial directory for native dialogs."""
        candidate = ''
        # if self._path_input is not None:
        #     candidate = str(self._path_input.value or '').strip()
        if candidate:
            p = Path(candidate).expanduser()
            if p.is_dir():
                return p
            if p.parent.exists():
                return p.parent

        last_path = self.app_config.get_last_path().strip()
        if last_path:
            p = Path(last_path).expanduser()
            if p.is_dir():
                return p
            if p.parent.exists():
                return p.parent
        return Path.home()

    def _notify_status(self, message: str, level: str) -> None:
        """Send a status notification safely from foreground or background tasks."""
        try:
            ui.notify(message, type=level)
            return
        except RuntimeError:
            # Background tasks may not have an active slot/client context.
            pass

        if self._client is None:
            logger.warning('Notification dropped (no client context): %s', message)
            return

        payload = {
            'message': message,
            'type': level,
        }
        script = f"if(window.$q) window.$q.notify({json.dumps(payload)});"
        self._client.run_javascript(script)

    def _run_ui(self, fn: Callable[[], None]) -> None:
        """Run UI mutations that may be triggered without an active NiceGUI slot.

        Background tasks (e.g. after ``run.io_bound``) publish events on the bus;
        subscribers run in that task and lack slot/client context. Prefer normal
        execution; on failure use ``Client.safe_invoke`` to remarshal into the page
        client context.

        Args:
            fn: Callable that updates NiceGUI elements for this view.
        """
        try:
            fn()
        except RuntimeError as exc:
            message = str(exc).lower()
            if 'slot' not in message and 'client' not in message:
                raise
            if self._client is None:
                logger.warning('UI update dropped (no client): %s', exc)
                return
            self._client.safe_invoke(fn)
