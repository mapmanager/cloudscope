"""Load/save toolbar view for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import (
    AppStatusChanged,
    ClearRecentPathsIntent,
    FileSelectionChanged,
    LoadPathKind,
    LoadPathIntent,
    RecentPathsChanged,
    SaveAllIntent,
    SaveSelectedIntent,
    TaskProgressChanged,
)
from cloudscope.gui.app_config import AppConfig


@dataclass
class LoadSaveView:
    """Toolbar that emits load/save intents and renders recents/progress UI."""

    event_bus: EventBus
    app_config: AppConfig

    def __post_init__(self) -> None:
        self._path_input: ui.input | None = None
        self._save_selected_button: ui.button | None = None
        self._save_all_button: ui.button | None = None
        self._current_file_id: str | None = None
        self._current_file_dirty: bool = False
        self._progress_dialog: ui.dialog | None = None
        self._progress_bar: ui.linear_progress | None = None
        self._progress_label: ui.label | None = None
        self._progress_message: ui.label | None = None

        self.event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self.event_bus.subscribe(RecentPathsChanged, self._on_recent_paths_changed)
        self.event_bus.subscribe(TaskProgressChanged, self._on_task_progress_changed)
        self.event_bus.subscribe(AppStatusChanged, self._on_status_changed)

    def build(self) -> None:
        """Build toolbar UI."""
        with ui.row().classes('w-full items-center gap-2'):
            self._path_input = ui.input(
                label='Path',
                placeholder='Enter file/folder/csv path then click load button',
            ).classes('grow')

            with ui.button(icon='history').props('flat dense'):
                with ui.menu() as menu:
                    self._build_recent_menu(menu)

            ui.button('Load File', on_click=lambda: self._emit_load(LoadPathKind.FILE)).props('dense')
            ui.button('Load Folder', on_click=lambda: self._emit_load(LoadPathKind.FOLDER)).props('dense')
            ui.button('Load CSV', on_click=lambda: self._emit_load(LoadPathKind.CSV)).props('dense')

            self._save_selected_button = ui.button(
                'Save Selected',
                on_click=lambda: self.event_bus.publish(SaveSelectedIntent()),
            ).props('dense')
            self._save_all_button = ui.button(
                'Save All',
                on_click=lambda: self.event_bus.publish(SaveAllIntent()),
            ).props('dense')

        self._build_progress_dialog()
        self._update_button_states()

    def _build_progress_dialog(self) -> None:
        with ui.dialog() as dialog, ui.card().classes('w-[460px]'):
            self._progress_label = ui.label('Task').classes('text-lg font-semibold')
            self._progress_message = ui.label('').classes('text-sm text-gray-600')
            self._progress_bar = ui.linear_progress(value=0.0).classes('w-full')
        self._progress_dialog = dialog

    def _build_recent_menu(self, menu: ui.menu) -> None:
        recent_folders = self.app_config.get_recent_folders()
        recent_files = self.app_config.get_recent_files()
        with menu:
            for item in recent_folders:
                ui.menu_item(f'Folder: {item}', lambda p=item: self._load_recent(p, LoadPathKind.FOLDER))
            if recent_folders and recent_files:
                ui.separator()
            for item in recent_files:
                kind = LoadPathKind.CSV if item.lower().endswith('.csv') else LoadPathKind.FILE
                ui.menu_item(f'File: {item}', lambda p=item, k=kind: self._load_recent(p, k))
            if recent_folders or recent_files:
                ui.separator()
                ui.menu_item('Clear recents', lambda: self.event_bus.publish(ClearRecentPathsIntent()))

    def _emit_load(self, kind: LoadPathKind) -> None:
        if self._path_input is None:
            return
        path = str(self._path_input.value or '').strip()
        if not path:
            ui.notify('Enter a path before loading', type='warning')
            return
        self.event_bus.publish(LoadPathIntent(path=path, kind=kind))

    def _load_recent(self, path: str, kind: LoadPathKind) -> None:
        if self._path_input is not None:
            self._path_input.value = path
        self.event_bus.publish(LoadPathIntent(path=path, kind=kind))

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        self._current_file_id = event.file_id
        self._current_file_dirty = bool(event.acq_image is not None and event.acq_image.is_dirty)
        self._update_button_states()

    def _on_recent_paths_changed(self, _event: RecentPathsChanged) -> None:
        # The menu is reconstructed on next page render; no immediate mutation needed.
        pass

    def _on_status_changed(self, event: AppStatusChanged) -> None:
        ui.notify(event.message, type=event.level.value)

    def _on_task_progress_changed(self, event: TaskProgressChanged) -> None:
        if self._progress_dialog is None or self._progress_bar is None or self._progress_label is None or self._progress_message is None:
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

    def _update_button_states(self) -> None:
        if self._save_selected_button is not None:
            if self._current_file_id is None or not self._current_file_dirty:
                self._save_selected_button.disable()
            else:
                self._save_selected_button.enable()
        if self._save_all_button is not None:
            self._save_all_button.enable()
