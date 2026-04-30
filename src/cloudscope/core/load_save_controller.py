"""Load/save orchestration controller for CloudScope."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

from acqstore.acq_image.acq_image_list import AcqImageList, LoadResult
from nicegui import run
from cloudscope.core.home_page_controller import HomePageController
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import (
    AppStatusChanged,
    ClearRecentPathsIntent,
    LoadPathKind,
    LoadPathIntent,
    RecentPathsChanged,
    RemoveRecentPathIntent,
    SaveAllIntent,
    SaveSelectedIntent,
    StatusLevel,
    StatusSource,
    TaskKind,
    TaskStatus,
    TaskProgressChanged,
)
from cloudscope.core.utils.logging import get_logger
from cloudscope.gui.app_config import AppConfig, normalize_stored_path

logger = get_logger(__name__)


@dataclass(slots=True)
class LoadSaveController:
    """Coordinate load/save intents and publish progress/status state events."""

    event_bus: EventBus
    home_controller: HomePageController
    app_config: AppConfig

    def bind(self) -> None:
        """Subscribe controller handlers to load/save intents."""
        self.event_bus.subscribe(LoadPathIntent, self._on_load_path)
        self.event_bus.subscribe(RemoveRecentPathIntent, self._on_remove_recent_path)
        self.event_bus.subscribe(SaveSelectedIntent, self._on_save_selected)
        self.event_bus.subscribe(SaveAllIntent, self._on_save_all)
        self.event_bus.subscribe(ClearRecentPathsIntent, self._on_clear_recent_paths)

    def _on_load_path(self, event: LoadPathIntent) -> None:
        """Schedule async load path orchestration."""
        self._schedule(self._on_load_path_async(event))

    async def _on_load_path_async(self, event: LoadPathIntent) -> None:
        """Load path via backend safe loader and push state events."""
        task_id = str(uuid4())
        task_label = f'Load {event.kind}'
        self._publish_task(
            task_kind=TaskKind.LOAD,
            task_id=task_id,
            task_label=task_label,
            status=TaskStatus.RUNNING,
            current=0,
            total=1,
            message=f'Loading {event.kind}: {event.path}',
        )
        logger.info('load path intent kind=%s path=%s', event.kind, event.path)

        folder_depth = int(self.app_config.get_attribute('folder_depth'))
        if event.kind == LoadPathKind.FOLDER:
            result = await run.io_bound(
                AcqImageList.load_safe,
                event.path,
                kind=event.kind,
                folder_depth=folder_depth,
            )
        else:
            result = await run.io_bound(AcqImageList.load_safe, event.path, kind=event.kind)
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
            self._update_recents(path=event.path, kind=event.kind)
        self._publish_task(
            task_kind=TaskKind.LOAD,
            task_id=task_id,
            task_label=task_label,
            status=TaskStatus.COMPLETED,
            current=1,
            total=1,
            message=f'Loaded {len(loaded)} file(s)',
        )

    def _on_save_selected(self, _event: SaveSelectedIntent) -> None:
        """Schedule async save-selected orchestration."""
        self._schedule(self._on_save_selected_async())

    async def _on_save_selected_async(self) -> None:
        """Save currently selected file if dirty."""
        task_id = str(uuid4())
        task_label = 'Save selected'
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

        self._publish_task(TaskKind.SAVE, task_id, task_label, TaskStatus.RUNNING, 0, 1, f'Saving {selection.file_id}')
        logger.info('saving selected file_id=%s', selection.file_id)
        await run.io_bound(acq_file.save)
        self._publish_task(TaskKind.SAVE, task_id, task_label, TaskStatus.COMPLETED, 1, 1, f'Saved {selection.file_id}')
        self._publish_status(level=StatusLevel.INFO, source=StatusSource.SAVE, message='Saved selected file')

    def _on_save_all(self, _event: SaveAllIntent) -> None:
        """Schedule async save-all orchestration."""
        self._schedule(self._on_save_all_async())

    async def _on_save_all_async(self) -> None:
        """Save all dirty files and publish progress."""
        acq_list = self.home_controller.state.acq_image_list
        if acq_list is None:
            self._publish_status(level=StatusLevel.WARNING, source=StatusSource.SAVE, message='No files loaded')
            return

        dirty_files = list(acq_list.get_dirty_files())
        total = len(dirty_files)
        if total == 0:
            self._publish_status(level=StatusLevel.INFO, source=StatusSource.SAVE, message='No dirty files to save')
            return

        task_id = str(uuid4())
        task_label = 'Save all'
        self._publish_task(TaskKind.SAVE, task_id, task_label, TaskStatus.RUNNING, 0, total, 'Saving dirty files')
        logger.info('saving all dirty files total=%d', total)
        completed = 0
        for acq_file in dirty_files:
            await run.io_bound(acq_file.save)
            completed += 1
            self._publish_task(
                TaskKind.SAVE,
                task_id,
                task_label,
                TaskStatus.RUNNING,
                completed,
                total,
                f'Saved {completed}/{total}',
            )
        self._publish_task(TaskKind.SAVE, task_id, task_label, TaskStatus.COMPLETED, total, total, f'Saved {total}/{total}')
        self._publish_status(level=StatusLevel.INFO, source=StatusSource.SAVE, message='Save all completed')

    def _on_clear_recent_paths(self, _event: ClearRecentPathsIntent) -> None:
        """Clear recent file/folder paths and publish update."""
        self.app_config.clear_recent_paths()
        self.app_config.save()
        self._publish_recent_paths()
        self._publish_status(level=StatusLevel.INFO, source=StatusSource.SYSTEM, message='Cleared recent paths')

    def _on_remove_recent_path(self, event: RemoveRecentPathIntent) -> None:
        """Drop one recent path from config and persist."""
        self._remove_recent_path_entry(event.path, event.kind)

    def _remove_recent_path_entry(self, path: str, kind: LoadPathKind) -> None:
        if kind == LoadPathKind.FOLDER:
            self.app_config.remove_recent_folder(path)
        else:
            self.app_config.remove_recent_file(path)
        self.app_config.save()
        self._publish_recent_paths()

    @staticmethod
    def _recent_nominal_target_missing(result: LoadResult, path: str, kind: LoadPathKind) -> bool:
        """True when ``load_safe`` reported the nominal path missing or wrong type on disk."""
        _ = kind
        target = normalize_stored_path(path)
        for w in result.warnings:
            if w.path is None:
                continue
            if normalize_stored_path(w.path) != target:
                continue
            msg = (w.message or '').lower()
            if (
                'does not exist' in msg
                or 'is not a directory' in msg
                or 'is not a file' in msg
            ):
                return True
        return False

    def _update_recents(self, *, path: str, kind: LoadPathKind) -> None:
        """Update app config recents and last path after a load action."""
        if kind == LoadPathKind.FOLDER:
            self.app_config.push_recent_folder(path)
        else:
            self.app_config.push_recent_file(path)
        self.app_config.set_last_path(path)
        self.app_config.save()
        self._publish_recent_paths()

    def _publish_recent_paths(self) -> None:
        self.event_bus.publish(
            RecentPathsChanged(
                recent_files=self.app_config.get_recent_files(),
                recent_folders=self.app_config.get_recent_folders(),
            )
        )

    def _publish_status(self, *, level: StatusLevel, source: StatusSource, message: str) -> None:
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

    @staticmethod
    def _schedule(coro: object) -> None:
        """Run coroutine in active loop, or directly when no loop exists."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)
