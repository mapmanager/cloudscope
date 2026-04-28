"""Tests for load/save orchestration controller."""

from __future__ import annotations

from pathlib import Path

from acqstore.acq_image.acq_image_list import LoadResult, LoadWarning
from cloudscope.core.controller import HomePageController
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import (
    AppStatusChanged,
    LoadPathKind,
    LoadPathIntent,
    RecentPathsChanged,
    SaveAllIntent,
    SaveSelectedIntent,
    TaskProgressChanged,
)
from cloudscope.core.load_save_controller import LoadSaveController
from cloudscope.gui.app_config import AppConfig


class _FakeFile:
    def __init__(self, file_id: str, *, dirty: bool = False) -> None:
        self.file_id = file_id
        self._dirty = dirty
        self.saved = 0

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def save(self) -> None:
        self.saved += 1
        self._dirty = False

    def get_default_channel(self) -> int | None:
        return 0

    def get_default_roi(self) -> int | None:
        return None

    def get_schema_row(self) -> dict[str, object]:
        return {
            'name': Path(self.file_id).name,
            'path': self.file_id,
            'num_channels': 1,
            'num_rois': 0,
        }


class _FakeList:
    def __init__(self, files: list[_FakeFile]) -> None:
        self._files = files
        self._files_by_id = {item.file_id: item for item in files}

    def __len__(self) -> int:
        return len(self._files)

    def get_files(self):
        return tuple(self._files)

    def get_file_by_id(self, file_id: str):
        return self._files_by_id.get(file_id)

    def get_default_selection(self):
        first = self._files[0].file_id if self._files else None
        return (first, 0 if first else None, None)

    def get_schema_rows(self):
        return [item.get_schema_row() for item in self._files]

    def get_dirty_files(self):
        return tuple(item for item in self._files if item.is_dirty)

    def iter_save_all(self):
        total = len(self.get_dirty_files())
        completed = 0
        for item in self.get_dirty_files():
            from acqstore.acq_image.acq_image_list import SaveEvent, SaveProgress

            yield SaveProgress(event=SaveEvent.SAVING, completed=completed, total=total, file_id=item.file_id)
            item.save()
            completed += 1
            yield SaveProgress(event=SaveEvent.SAVED, completed=completed, total=total, file_id=item.file_id)


def test_load_path_emits_status_progress_and_recents(tmp_path, monkeypatch) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()

    fake_list = _FakeList([_FakeFile('/tmp/a.tif')])

    def _load_safe(_path: str, *, kind: str, **_kwargs):
        return LoadResult(acq_image_list=fake_list, warnings=(LoadWarning(message='warn'),))

    monkeypatch.setattr('cloudscope.core.load_save_controller.AcqImageList.load_safe', _load_safe)
    statuses: list[AppStatusChanged] = []
    progress: list[TaskProgressChanged] = []
    recents: list[RecentPathsChanged] = []
    bus.subscribe(AppStatusChanged, statuses.append)
    bus.subscribe(TaskProgressChanged, progress.append)
    bus.subscribe(RecentPathsChanged, recents.append)

    bus.publish(LoadPathIntent(path='/tmp/a.tif', kind=LoadPathKind.FILE))
    assert any(item.status == 'running' for item in progress)
    assert any(item.status == 'completed' for item in progress)
    assert statuses[-1].level == 'warning'
    assert recents[-1].recent_files[-1].endswith('a.tif')


def test_save_selected_requires_dirty_selected_file(tmp_path) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()
    home.bind()

    statuses: list[AppStatusChanged] = []
    bus.subscribe(AppStatusChanged, statuses.append)
    bus.publish(SaveSelectedIntent())
    assert statuses[-1].message == 'No file selected to save'


def test_save_all_no_dirty_emits_info_status(tmp_path) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()
    home.state.acq_image_list = _FakeList([_FakeFile('/tmp/a.tif', dirty=False)])
    statuses: list[AppStatusChanged] = []
    bus.subscribe(AppStatusChanged, statuses.append)
    bus.publish(SaveAllIntent())
    assert statuses[-1].message == 'No dirty files to save'
