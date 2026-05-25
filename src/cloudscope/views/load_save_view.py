"""Load/save toolbar view for CloudScope."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

from nicegui import app, ui

from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import AcqImageEventsChanged
from cloudscope.events.analysis import AnalysisCompleted
from cloudscope.events.files import (
    ClearRecentPathsIntent,
    LoadPathIntent,
    LoadPathKind,
    RecentPathsChanged,
    RemoveRecentPathIntent,
    SaveAllIntent,
    SaveSelectedIntent,
)
from cloudscope.events.status import AppStatusChanged, StatusLevel, StatusSource
from cloudscope._py_web_view import _prompt_for_path
from cloudscope.app_config import AppConfig, normalize_stored_path
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId

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


class LoadSaveView(BaseView):
    """Toolbar that emits load/save intents and renders recents/progress UI.

    Args:
        event_bus: Page-scoped event bus.
        app_config: Shared app configuration for recents and native dialog defaults.
        initially_visible: Whether the view starts visible.
    """

    view_id = ViewId.LOAD_SAVE
    disable_when_busy = True

    def __init__(
        self,
        *,
        event_bus: EventBus,
        app_config: AppConfig,
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self.app_config = app_config
        self._save_selected_button: ui.button | None = None
        self._save_all_button: ui.button | None = None
        self._client = None
        self._history_menu_container: ui.element | None = None
        self._history_button: ui.button | None = None
        self._recent_menu: ui.menu | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build toolbar UI.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        self._client = ui.context.client
        if parent is None:
            with ui.row().classes('w-full items-center gap-2') as self.root:
                self._build_toolbar_contents()
        else:
            with parent:
                with ui.row().classes('w-full items-center gap-2') as self.root:
                    self._build_toolbar_contents()

        self._update_button_states()
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to load/save events while this view is visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(RecentPathsChanged, self._on_recent_paths_changed))
        self.add_subscription(self.event_bus.subscribe(AppStatusChanged, self._on_status_changed))
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))
        self.add_subscription(self.event_bus.subscribe(AcqImageEventsChanged, self._on_acq_image_events_changed))

    def _on_acq_image_events_changed(self, event: AcqImageEventsChanged) -> None:
        """Refresh save buttons when event analysis changes dirty state.

        Args:
            event: AcqImage events changed state event.

        Returns:
            None.
        """
        self._update_button_states()

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh button states when an analysis completes.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        self._update_button_states()
        
    def _build_toolbar_contents(self) -> None:
        """Build toolbar controls inside the current NiceGUI slot.

        Returns:
            None.
        """
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

    def _recent_item_matches_app_path(self, path: str) -> bool:
        """True when ``path`` is the same as persisted ``last_path`` (folder or file)."""
        last = self.app_config.get_last_path().strip()
        if not last:
            return False
        return normalize_stored_path(path) == normalize_stored_path(last)

    def _fill_recent_menu(self, menu: ui.menu) -> None:
        recent_folders = self.app_config.get_recent_folders()
        recent_files = self.app_config.get_recent_files()
        logger.info('recent_folders=%s recent_files=%s', recent_folders, recent_files)
        with menu:
            for item in recent_folders:
                mark = '✓ ' if self._recent_item_matches_app_path(item) else ''
                label = f'{mark}{_path_display(item)}'
                ui.menu_item(label, lambda p=item: self._load_recent(p, LoadPathKind.FOLDER))
            if recent_folders and recent_files:
                ui.separator()
            for item in recent_files:
                kind = LoadPathKind.CSV if item.lower().endswith('.csv') else LoadPathKind.FILE
                mark = '✓ ' if self._recent_item_matches_app_path(item) else ''
                label = f'{mark}{_path_display(item)}'
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

    def _on_save_selected_clicked(self) -> None:
        """Emit save-selected intent without asking for an analysis CSV path.

        Analysis result file names are backend-owned sidecar paths derived from
        the acquisition image path. The user should not be prompted for a CSV
        destination when saving an AcqImage.
        """
        self.event_bus.publish(SaveSelectedIntent())

    def _on_save_all_clicked(self) -> None:
        """Emit save-all intent without asking for an analysis CSV path.

        Analysis result file names are backend-owned sidecar paths derived from
        each acquisition image path.
        """
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

    def on_primary_selection_changed(self) -> None:
        """Update save-button state from the cached primary selection.

        Returns:
            None.
        """
        self._run_ui(self._update_button_states)

    def _on_recent_paths_changed(self, _event: RecentPathsChanged) -> None:
        def apply() -> None:
            self._rebuild_history_menu_impl()

        self._run_ui(apply)

    def _on_status_changed(self, event: AppStatusChanged) -> None:
        self._notify_status(event.message, event.level.value)

    def _update_button_states(self) -> None:
        """Update load/save button enabled state from current app state.

        Returns:
            None.
        """
        selected_acq_image = self.get_selected_acq_image()
        selected_is_dirty = self.selected_acq_image_is_dirty()

        if self._save_selected_button is not None:
            if selected_acq_image is None or not selected_is_dirty:
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
