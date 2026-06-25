"""Load/save toolbar view for CloudScope."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path

from nicegui import app, ui

from acqstore.acq_image.supported_import_extensions import get_allowed_import_extensions
from acqstore.upload_store import (
    UploadCollisionError,
    UploadError,
    store_uploaded_file,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import AcqImageEventsChanged
from cloudscope.events.analysis import AnalysisCompleted
from cloudscope.events.files import (
    ClearRecentPathsIntent,
    LoadPathIntent,
    LoadPathKind,
    LoadSampleDataIntent,
    RecentPathsChanged,
    RemoveRecentPathIntent,
    SaveAllIntent,
    SaveSelectedIntent,
)
from cloudscope.events.status import AppStatusChanged
from cloudscope._py_web_view import _prompt_for_path
from cloudscope.app_config import AppConfig, normalize_stored_path
from cloudscope.preset_data import get_manning_preset_path, is_loadable_preset_folder
from cloudscope.quota import QuotaExceededError, ensure_within_quota
from cloudscope.user_context import UserContext, UserContextKind
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.upload_widget import CancelToken, UploadWidget

logger = get_logger(__name__)

_UPLOAD_COMPACT_CSS_CLASS = 'cloudscope-upload-compact'
_UPLOAD_COMPACT_CSS = """
.q-uploader.cloudscope-upload-compact { width: fit-content; min-width: 0; }
.cloudscope-upload-compact { min-height: 36px; }
.cloudscope-upload-compact .q-uploader__list { display: none; }
.cloudscope-upload-compact .q-uploader__header-content { padding: 4px 8px; min-height: 36px; }
.cloudscope-upload-compact .q-uploader__title { font-size: 0.85rem; font-weight: 500; }
.cloudscope-upload-compact .q-uploader__subtitle { display: none; }
"""


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
        user_context: Optional user/workspace context for upload storage.
        initially_visible: Whether the view starts visible.
    """

    view_id = ViewId.LOAD_SAVE
    disable_when_busy = True

    def __init__(
        self,
        *,
        event_bus: EventBus,
        app_config: AppConfig,
        user_context: UserContext | None = None,
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self.app_config = app_config
        self.user_context = user_context
        self._save_selected_button: ui.button | None = None
        self._save_all_button: ui.button | None = None
        self._client = None
        self._history_menu_container: ui.element | None = None
        self._history_button: ui.button | None = None
        self._recent_menu: ui.menu | None = None
        self._upload_widget: UploadWidget | None = None
        self._upload_progress: _UploadProgressDialog | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build toolbar UI.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        # logger.info('!!! debug timeout reset')
        
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
        self._build_upload_control()

        self._save_selected_button = ui.button(
            'Save Selected',
            on_click=self._on_save_selected_clicked,
        ).classes('ml-auto')
        self._save_all_button = ui.button(
            'Save All',
            on_click=self._on_save_all_clicked,
        )

    def _build_upload_control(self) -> None:
        """Mount the inline compact upload widget that doubles as a drop target.

        Skipped in native mode: native runs use the pywebview file picker via
        ``Load File`` and do not support the browser ``ui.upload`` flow, so the
        upload control is only built for browser/remote runs.

        Returns:
            None.
        """
        if self._is_native_mode():
            return
        ui.add_css(_UPLOAD_COMPACT_CSS)
        with ui.element('div').classes('inline-flex items-center shrink-0'):
            self._upload_widget = UploadWidget(
                label='Upload File',
                accept=_accepted_upload_extensions(),
                multiple=False,
                max_files=1,
                on_paths_ready=self._on_upload_paths_ready,
                on_progress=self._on_upload_progress,
                show_inline_status=False,
                extra_props='flat dense bordered hide-upload-btn no-thumbnails',
                extra_classes=_UPLOAD_COMPACT_CSS_CLASS,
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
        # logger.info('recent_folders=%s recent_files=%s', recent_folders, recent_files)
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
            ui.menu_item('Load CSV', lambda: self._on_load_clicked(LoadPathKind.CSV))
            ui.menu_item('Load Sample Data', self._on_load_sample_data_clicked)
            self._append_manning_preset_menu_item()
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
        self._history_button.enable()

    # def _emit_load(self, kind: LoadPathKind) -> None:
    #     if self._path_input is None:
    #         return
    #     path = str(self._path_input.value or '').strip()
    #     if not path:
    #         ui.notify('Enter a path before loading', type='warning')
    #         return
    #     self.event_bus.publish(LoadPathIntent(path=path, kind=kind))

    def _on_load_sample_data_clicked(self) -> None:
        """Emit a request to load the default sample dataset."""
        self.event_bus.publish(LoadSampleDataIntent(name='demo-small'))

    def _manning_preset_load_path(self) -> Path | None:
        """Return the Manning preset path for server/docker contexts.

        Returns:
            Configured preset directory, or ``None`` when not offered.
        """
        if self.user_context is None:
            return None
        if self.user_context.kind is UserContextKind.LOCAL_OS_USER:
            return None
        return get_manning_preset_path()

    def _append_manning_preset_menu_item(self) -> None:
        """Add the Manning velocity preset load item for remote/server runs.

        Returns:
            None.
        """
        preset_path = self._manning_preset_load_path()
        if preset_path is None:
            return

        item = ui.menu_item('Load Manning Velocity 2026', self._on_load_manning_preset_clicked)
        if not is_loadable_preset_folder(preset_path):
            item.disable()

    def _on_load_manning_preset_clicked(self) -> None:
        """Emit a folder load for the configured Manning preset path."""
        preset_path = self._manning_preset_load_path()
        if preset_path is None or not is_loadable_preset_folder(preset_path):
            return
        self.event_bus.publish(
            LoadPathIntent(
                path=str(preset_path),
                kind=LoadPathKind.FOLDER,
                from_recent=False,
            ),
        )

    def _on_upload_progress(self, fraction: float, message: str | None) -> None:
        """Update or open the upload progress dialog from widget progress events.

        Args:
            fraction: Progress fraction in ``[0.0, 1.0]``.
            message: Optional human-readable status message.

        Returns:
            None.
        """
        if self._upload_progress is None:
            self._upload_progress = self._open_upload_progress_dialog()
        if message is not None:
            self._upload_progress.set_status(message)
        if fraction >= 1.0:
            self._close_upload_progress_dialog()

    async def _on_upload_paths_ready(self, paths: list[Path], cancel: CancelToken) -> None:
        """Persist uploaded paths and emit a load intent.

        Args:
            paths: Normalized upload paths produced by the upload widget.
            cancel: Cancellation token shared with the upload widget.

        Returns:
            None.
        """
        if cancel.cancelled or not paths:
            return
        source_path = paths[0]
        widget = self._upload_widget
        original_filename = (
            widget.get_original_filename(source_path) if widget is not None else source_path.name
        )
        if self._upload_progress is None:
            self._upload_progress = self._open_upload_progress_dialog()
        self._upload_progress.set_status(f'Storing {original_filename}…')
        result = self._handle_upload_paths(source_path=source_path, original_filename=original_filename)
        if result.intent is not None:
            self.event_bus.publish(result.intent)
        if result.notify is not None:
            ui.notify(result.notify.message, type=result.notify.type)

    def _handle_upload_paths(
        self,
        *,
        source_path: Path,
        original_filename: str,
    ) -> _UploadOutcome:
        """Persist one upload and decide on follow-up intent and user notice.

        Args:
            source_path: Normalized upload path on disk.
            original_filename: Original filename supplied by the browser.

        Returns:
            Outcome describing whether to publish a load intent and what user
            notification (if any) to surface.
        """
        try:
            upload_dir = self.user_context.upload_dir if self.user_context is not None else None
            if self.user_context is not None:
                try:
                    incoming_bytes = source_path.stat().st_size
                except OSError:
                    incoming_bytes = 0
                ensure_within_quota(
                    root=self.user_context.data_dir,
                    incoming_bytes=incoming_bytes,
                    quota_bytes=self.user_context.quota_bytes,
                    max_upload_bytes=self.user_context.max_upload_bytes,
                )
            stored_path = store_uploaded_file(
                source_path,
                original_filename=original_filename,
                upload_dir=upload_dir,
            )
            if self.user_context is not None:
                self.user_context.touch_last_used()
        except QuotaExceededError as exc:
            logger.warning('Upload rejected by quota: %s', exc)
            return _UploadOutcome(notify=_UploadNotice(message=str(exc), type='warning'))
        except UploadCollisionError as exc:
            logger.warning('Upload collision: %s', exc)
            return _UploadOutcome(
                notify=_UploadNotice(message=f'File already exists: {original_filename}', type='warning'),
            )
        except (UploadError, ValueError) as exc:
            logger.warning('Upload rejected: %s', exc)
            return _UploadOutcome(notify=_UploadNotice(message=str(exc), type='warning'))
        except Exception as exc:
            logger.exception('Upload failed')
            return _UploadOutcome(notify=_UploadNotice(message=f'Upload failed: {exc}', type='negative'))

        return _UploadOutcome(
            intent=LoadPathIntent(
                path=str(stored_path),
                kind=LoadPathKind.FILE,
                from_recent=False,
            ),
            notify=_UploadNotice(message=f'Uploaded {stored_path.name}', type='positive'),
        )

    def _open_upload_progress_dialog(self) -> _UploadProgressDialog:
        """Create and open a persistent upload progress dialog.

        Returns:
            Handle bundling the dialog and its status label.
        """
        with ui.dialog().props('persistent') as dialog, ui.card().classes('w-[360px]'):
            ui.label('Uploading file').classes('text-base font-semibold')
            with ui.row().classes('items-center gap-3 w-full'):
                ui.spinner(size='md')
                status_label = ui.label('Upload received').classes('text-sm text-gray-700')
            with ui.row().classes('justify-end w-full'):
                ui.button('Cancel', on_click=self._on_upload_cancel_clicked).props('flat')
        dialog.open()
        return _UploadProgressDialog(dialog=dialog, status_label=status_label)

    def _close_upload_progress_dialog(self) -> None:
        """Close and forget the active upload progress dialog if any."""
        progress = self._upload_progress
        self._upload_progress = None
        if progress is None:
            return
        try:
            progress.dialog.close()
        except Exception:
            logger.debug('upload progress dialog close failed', exc_info=True)
        if self._upload_widget is not None:
            self._upload_widget.reset_cancel()

    def _on_upload_cancel_clicked(self) -> None:
        """Cancel the current upload and close the progress dialog.

        Returns:
            None.
        """
        if self._upload_widget is not None:
            self._upload_widget.cancel()
        self._close_upload_progress_dialog()

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
        """Return whether desktop pywebview file pickers should be used."""
        from cloudscope.desktop_launcher import get_pool_launcher

        if get_pool_launcher() is not None:
            return True
        native = getattr(app, 'native', None)
        return getattr(native, 'main_window', None) is not None

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


def _accepted_upload_extensions() -> str:
    """Return browser accept text for acquisition uploads."""
    return ','.join(f'.{extension}' for extension in get_allowed_import_extensions())


@dataclass(slots=True)
class _UploadNotice:
    """User-visible notification produced by the upload pipeline."""

    message: str
    type: str


@dataclass(slots=True)
class _UploadOutcome:
    """Result of persisting one uploaded file.

    Attributes:
        intent: Optional load intent to publish on success.
        notify: Optional user-facing notice to surface.
    """

    intent: LoadPathIntent | None = None
    notify: _UploadNotice | None = None


@dataclass(slots=True)
class _UploadProgressDialog:
    """Handle to an open upload progress dialog.

    Attributes:
        dialog: The dialog element.
        status_label: Inline label updated during upload progress.
    """

    dialog: ui.dialog
    status_label: ui.label

    def set_status(self, message: str) -> None:
        """Update the inline status text.

        Args:
            message: Status text to display.

        Returns:
            None.
        """
        self.status_label.text = message
