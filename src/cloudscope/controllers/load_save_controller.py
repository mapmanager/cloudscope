"""Load/save workflow controller for CloudScope."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from acqstore.acq_image.acq_image_list import (
    AcqImageList,
    LoadCancelled,
    LoadResult,
    LoadWarning,
    PathKind,
    SaveEvent,
)

from cloudscope.app_config import AppConfig, normalize_stored_path
from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    CancelTaskIntent,
    TaskKind,
    TaskProgressChanged,
    TaskStatus,
)
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
from cloudscope.task_runner import TaskCancelled, TaskContext, TaskRunner
from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


class _ImmediateTaskContext:
    """Small synchronous task context used when no ``TaskRunner`` is attached.

    Args:
        task_kind: Task kind used for progress publication.
        task_id: Synthetic task id.
        event_bus: Page-scoped event bus.
        task_label: Human-readable task label.
    """

    def __init__(
        self,
        *,
        task_kind: TaskKind,
        task_id: str,
        event_bus: EventBus,
        task_label: str,
    ) -> None:
        self.task_kind = task_kind
        self.task_id = task_id
        self._event_bus = event_bus
        self._task_label = task_label

    def report_progress(self, fraction: float | None, message: str = '') -> None:
        """Publish immediate progress.

        Args:
            fraction: Fraction complete, or None when unknown.
            message: Human-readable progress message.

        Returns:
            None.
        """
        current = 0 if fraction is None else max(0, min(100, int(round(float(fraction) * 100))))
        self._event_bus.publish(
            TaskProgressChanged(
                task_kind=self.task_kind,
                task_id=self.task_id,
                task_label=self._task_label,
                status=TaskStatus.RUNNING,
                current=current,
                total=100,
                message=message,
            )
        )

    def is_cancelled(self) -> bool:
        """Return whether cancellation was requested.

        Returns:
            Always False for immediate fallback execution.
        """
        return False

    def raise_if_cancelled(self) -> None:
        """Raise when cancellation was requested.

        Returns:
            None.
        """


@dataclass(slots=True)
class LoadSaveController:
    """Coordinate load/save intents and long-running task execution.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: State-owner controller for loaded files and selection.
        app_config: Shared app configuration.
        task_runner: Optional single-active-task runner. When absent, operations
            run synchronously for tests and non-NiceGUI contexts.
    """

    event_bus: EventBus
    home_controller: HomePageController
    app_config: AppConfig
    task_runner: TaskRunner | None = None

    def bind(self) -> None:
        """Subscribe controller handlers to load/save intents.

        Returns:
            None.
        """
        self.event_bus.subscribe(LoadPathIntent, self._on_load_path)
        self.event_bus.subscribe(RemoveRecentPathIntent, self._on_remove_recent_path)
        self.event_bus.subscribe(SaveSelectedIntent, self._on_save_selected)
        self.event_bus.subscribe(SaveAllIntent, self._on_save_all)
        self.event_bus.subscribe(ClearRecentPathsIntent, self._on_clear_recent_paths)
        self.event_bus.subscribe(CancelTaskIntent, self._on_cancel_task)

    def _on_load_path(self, event: LoadPathIntent) -> None:
        """Start a load task.

        Args:
            event: Load-path intent.

        Returns:
            None.
        """
        task_label = f'Load {event.kind}'
        try:
            self._start_task(
                task_kind=TaskKind.LOAD,
                task_label=task_label,
                worker=lambda context: self._load_path_worker(event, context),
                on_completed=lambda result: self._finish_load(event, result),
                on_failed=lambda exc: self._publish_status(
                    level=StatusLevel.ERROR,
                    source=StatusSource.LOAD,
                    message=f'Load failed: {exc}',
                ),
                on_cancelled=lambda: self._publish_status(
                    level=StatusLevel.WARNING,
                    source=StatusSource.LOAD,
                    message='Load cancelled',
                ),
            )
        except RuntimeError as exc:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.LOAD, message=str(exc))

    def _on_save_selected(self, _event: SaveSelectedIntent) -> None:
        """Start save-selected task when possible.

        Args:
            _event: Save-selected intent.

        Returns:
            None.
        """
        selection = self.home_controller.state.selection
        acq_list = self.home_controller.state.acq_image_list
        if selection.file_id is None or acq_list is None:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SAVE, message='No file selected to save')
            return
        acq_file = acq_list.get_file_by_id(selection.file_id)
        if acq_file is None:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SAVE, message='Selected file no longer exists')
            return
        if not acq_file.is_dirty:
            self._publish_status(level=StatusLevel.INFO, source=StatusSource.SAVE, message='Selected file has no unsaved changes')
            return

        try:
            self._start_task(
                task_kind=TaskKind.SAVE,
                task_label='Save selected',
                worker=lambda context: self._save_selected_worker(acq_file, context),
                on_completed=lambda _result: self._publish_status(
                    level=StatusLevel.INFO,
                    source=StatusSource.SAVE,
                    message='Saved selected file',
                ),
                on_failed=lambda exc: self._publish_status(
                    level=StatusLevel.ERROR,
                    source=StatusSource.SAVE,
                    message=f'Save failed: {exc}',
                ),
                on_cancelled=lambda: self._publish_status(
                    level=StatusLevel.WARNING,
                    source=StatusSource.SAVE,
                    message='Save cancelled',
                ),
            )
        except RuntimeError as exc:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SAVE, message=str(exc))

    def _on_save_all(self, _event: SaveAllIntent) -> None:
        """Start save-all task when possible.

        Args:
            _event: Save-all intent.

        Returns:
            None.
        """
        acq_list = self.home_controller.state.acq_image_list
        if acq_list is None:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SAVE, message='No files loaded')
            return
        dirty_files = tuple(acq_list.get_dirty_files())
        if not dirty_files:
            self._publish_status(level=StatusLevel.INFO, source=StatusSource.SAVE, message='No dirty files to save')
            return

        try:
            self._start_task(
                task_kind=TaskKind.SAVE,
                task_label='Save all',
                worker=lambda context: self._save_all_worker(acq_list, context),
                on_completed=lambda _result: self._publish_status(
                    level=StatusLevel.INFO,
                    source=StatusSource.SAVE,
                    message='Save all completed',
                ),
                on_failed=lambda exc: self._publish_status(
                    level=StatusLevel.ERROR,
                    source=StatusSource.SAVE,
                    message=f'Save all failed: {exc}',
                ),
                on_cancelled=lambda: self._publish_status(
                    level=StatusLevel.WARNING,
                    source=StatusSource.SAVE,
                    message='Save cancelled',
                ),
            )
        except RuntimeError as exc:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SAVE, message=str(exc))

    def _on_cancel_task(self, event: CancelTaskIntent) -> None:
        """Cancel load/save tasks owned by this controller.

        Args:
            event: Cancel-task intent.

        Returns:
            None.
        """
        if event.task_kind not in (TaskKind.LOAD, TaskKind.SAVE):
            return
        if self.task_runner is None:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SYSTEM, message='No cancellable task runner is attached')
            return
        cancelled = self.task_runner.cancel(task_kind=event.task_kind, task_id=event.task_id)
        if not cancelled:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SYSTEM, message='No matching task is running')

    def _load_path_worker(self, event: LoadPathIntent, context: TaskContext | _ImmediateTaskContext) -> LoadResult:
        """Load files in a worker context.

        Args:
            event: Load intent.
            context: Task context for progress and cancellation.

        Returns:
            Load result.

        Raises:
            TaskCancelled: If loading is cancelled.
        """
        folder_depth = int(self.app_config.get_attribute('folder_depth'))

        def report(completed: int, total: int, message: str) -> None:
            fraction = None if total <= 0 else completed / total
            context.report_progress(fraction, message)

        try:
            return AcqImageList.load_safe(
                event.path,
                kind=PathKind(event.kind.value),
                folder_depth=folder_depth,
                progress_callback=report,
                should_cancel=context.is_cancelled,
            )
        except LoadCancelled as exc:
            raise TaskCancelled(str(exc)) from exc

    def _save_selected_worker(self, acq_file: object, context: TaskContext | _ImmediateTaskContext) -> None:
        """Save one file in a worker context.

        Args:
            acq_file: Acquisition file object exposing ``save`` and ``file_id``.
            context: Task context for progress and cancellation.

        Returns:
            None.

        Raises:
            TaskCancelled: If cancellation is requested before saving.
        """
        context.raise_if_cancelled()
        file_id = str(getattr(acq_file, 'file_id', 'selected file'))
        context.report_progress(0.0, f'Saving {file_id}')
        acq_file.save()
        context.report_progress(1.0, f'Saved {file_id}')

    def _save_all_worker(self, acq_list: AcqImageList, context: TaskContext | _ImmediateTaskContext) -> None:
        """Save dirty files in a worker context.

        Args:
            acq_list: Acquisition image list.
            context: Task context for progress and cancellation.

        Returns:
            None.

        Raises:
            TaskCancelled: If cancellation is requested between files.
        """
        for event in acq_list.iter_save_all(should_cancel=context.is_cancelled):
            if event.event is SaveEvent.CANCELLED:
                context.report_progress(
                    None if event.total <= 0 else event.completed / event.total,
                    f'Save cancelled after {event.completed}/{event.total}',
                )
                raise TaskCancelled('Save cancelled')
            fraction = None if event.total <= 0 else event.completed / event.total
            if event.event is SaveEvent.SAVING:
                context.report_progress(fraction, f'Saving {event.file_id}')
            elif event.event is SaveEvent.SAVED:
                context.report_progress(fraction, f'Saved {event.completed}/{event.total}')

    def _finish_load(self, event: LoadPathIntent, result: LoadResult) -> None:
        """Apply a completed load result to app state.

        Args:
            event: Original load intent.
            result: Completed load result.

        Returns:
            None.
        """
        warning_count = len(result.warnings)
        if warning_count:
            for warning in result.warnings:
                logger.warning(
                    'Load warning path=%s row=%s msg=%s',
                    warning.path,
                    warning.row_index,
                    warning.message,
                )
            self._publish_status(
                level=StatusLevel.WARNING,
                source=StatusSource.LOAD,
                message=f'Load completed with {warning_count} warning(s)',
            )
        else:
            self._publish_status(level=StatusLevel.INFO, source=StatusSource.LOAD, message='Load completed')

        loaded = result.acq_image_list
        if len(loaded) == 0:
            self.home_controller.load_demo_files([])
        else:
            self.home_controller.load_acq_image_list(loaded)

        stale_recent = event.from_recent and self._recent_nominal_target_missing(result, event.path, event.kind)
        if stale_recent:
            self._remove_recent_path_entry(event.path, event.kind)
        else:
            self._update_recents(path=event.path, kind=event.kind, from_recent=event.from_recent)

    def _on_clear_recent_paths(self, _event: ClearRecentPathsIntent) -> None:
        """Clear recent file/folder paths and publish update.

        Args:
            _event: Clear-recents intent.

        Returns:
            None.
        """
        self.app_config.clear_recent_paths()
        self.app_config.save()
        self._publish_recent_paths()
        self._publish_status(level=StatusLevel.INFO, source=StatusSource.SYSTEM, message='Cleared recent paths')

    def _on_remove_recent_path(self, event: RemoveRecentPathIntent) -> None:
        """Drop one recent path from config and persist.

        Args:
            event: Remove-recent-path intent.

        Returns:
            None.
        """
        self._remove_recent_path_entry(event.path, event.kind)

    def _remove_recent_path_entry(self, path: str, kind: LoadPathKind) -> None:
        """Remove one recent path and publish recents.

        Args:
            path: Recent path to remove.
            kind: Recent path kind.

        Returns:
            None.
        """
        if kind == LoadPathKind.FOLDER:
            self.app_config.remove_recent_folder(path)
        else:
            self.app_config.remove_recent_file(path)
        self.app_config.save()
        self._publish_recent_paths()

    @staticmethod
    def _recent_nominal_target_missing(result: LoadResult, path: str, kind: LoadPathKind) -> bool:
        """Return whether a recent-path load failed because the nominal path is stale.

        Args:
            result: Load result containing warnings.
            path: Original load path.
            kind: Original load kind.

        Returns:
            True when the nominal recent target is missing or has the wrong shape.
        """
        _ = kind
        target = normalize_stored_path(path)
        for warning in result.warnings:
            if warning.path is None:
                continue
            if normalize_stored_path(warning.path) != target:
                continue
            msg = (warning.message or '').lower()
            if 'does not exist' in msg or 'is not a directory' in msg or 'is not a file' in msg:
                return True
        return False

    def _update_recents(self, *, path: str, kind: LoadPathKind, from_recent: bool = False) -> None:
        """Update persisted recent paths after successful load completion.

        Args:
            path: Loaded path.
            kind: Loaded path kind.
            from_recent: Whether the path came from the recents menu.

        Returns:
            None.
        """
        if not from_recent:
            if kind == LoadPathKind.FOLDER:
                self.app_config.push_recent_folder(path)
            else:
                self.app_config.push_recent_file(path)
        self.app_config.set_last_path(path)
        self.app_config.save()
        self._publish_recent_paths()

    def _publish_recent_paths(self) -> None:
        """Publish current recent paths.

        Returns:
            None.
        """
        self.event_bus.publish(
            RecentPathsChanged(
                recent_files=self.app_config.get_recent_files(),
                recent_folders=self.app_config.get_recent_folders(),
            )
        )

    def _publish_status(self, *, level: StatusLevel, source: StatusSource, message: str) -> None:
        """Publish app status.

        Args:
            level: Status severity.
            source: Status source.
            message: User-visible status message.

        Returns:
            None.
        """
        logger.info('app status level=%s source=%s msg=%s', level, source, message)
        self.event_bus.publish(AppStatusChanged(level=level, source=source, message=message))

    def _publish_task(
        self,
        task_kind: TaskKind,
        task_id: str,
        task_label: str,
        status: TaskStatus,
        current: int,
        total: int,
        message: str,
    ) -> None:
        """Publish task progress.

        Args:
            task_kind: Task kind.
            task_id: Task id.
            task_label: Human-readable task label.
            status: Task lifecycle status.
            current: Current progress count.
            total: Total progress count.
            message: Human-readable progress message.

        Returns:
            None.
        """
        logger.info(
            'task progress kind=%s id=%s status=%s current=%d total=%d msg=%s',
            task_kind,
            task_id,
            status,
            current,
            total,
            message,
        )
        self.event_bus.publish(
            TaskProgressChanged(
                task_kind=task_kind,
                task_id=task_id,
                task_label=task_label,
                status=status,
                current=current,
                total=total,
                message=message,
            )
        )

    def _start_task(
        self,
        *,
        task_kind: TaskKind,
        task_label: str,
        worker: Callable[[TaskContext | _ImmediateTaskContext], object],
        on_completed: Callable[[object], None] | None = None,
        on_failed: Callable[[BaseException], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
    ) -> None:
        """Start task through ``TaskRunner`` or synchronous fallback.

        Args:
            task_kind: Task kind.
            task_label: Human-readable task label.
            worker: Worker callable.
            on_completed: Optional completion callback.
            on_failed: Optional failure callback.
            on_cancelled: Optional cancelled callback.

        Returns:
            None.
        """
        if self.task_runner is not None:
            self.task_runner.start(
                task_kind=task_kind,
                task_label=task_label,
                worker=worker,
                on_completed=on_completed,
                on_failed=on_failed,
                on_cancelled=on_cancelled,
            )
            return

        task_id = uuid4().hex
        self._publish_task(task_kind, task_id, task_label, TaskStatus.RUNNING, 0, 100, 'Running')
        context = _ImmediateTaskContext(
            task_kind=task_kind,
            task_id=task_id,
            event_bus=self.event_bus,
            task_label=task_label,
        )
        try:
            result = worker(context)
        except TaskCancelled:
            self._publish_task(task_kind, task_id, task_label, TaskStatus.CANCELLED, 0, 100, 'Cancelled')
            if on_cancelled is not None:
                on_cancelled()
            return
        except BaseException as exc:
            self._publish_task(task_kind, task_id, task_label, TaskStatus.FAILED, 0, 100, str(exc))
            if on_failed is not None:
                on_failed(exc)
            return
        self._publish_task(task_kind, task_id, task_label, TaskStatus.COMPLETED, 100, 100, 'Completed')
        if on_completed is not None:
            on_completed(result)
