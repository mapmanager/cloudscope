"""Tests for load/save orchestration controller."""

from __future__ import annotations

import json
from pathlib import Path

from acqstore.acq_image.acq_image import parent_grandparent_folder_names
from acqstore.acq_image.acq_image_list import AcqImageList, LoadResult, LoadWarning
from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AppStatusChanged,
    LoadPathKind,
    LoadPathIntent,
    RecentPathsChanged,
    RemoveRecentPathIntent,
    SaveAllIntent,
    SaveSelectedIntent,
    TaskProgressChanged,
)
from cloudscope.controllers.load_save_controller import LoadSaveController
from cloudscope.app_config import AppConfig, normalize_stored_path


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
        parent, grandparent = parent_grandparent_folder_names(
            self.file_id,
            loaded_from_stream=False,
        )
        return {
            'name': Path(self.file_id).name,
            'path': self.file_id,
            'parent': parent,
            'grandparent': grandparent,
            'genotype': '',
            'num_channels': 1,
            'num_rois': 0,
            'accept': True,
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

    monkeypatch.setattr('cloudscope.controllers.load_save_controller.AcqImageList.load_safe', _load_safe)
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
    saved = json.loads(cfg.path.read_text(encoding='utf-8'))
    assert saved['last_path']
    assert any(str(p).endswith('a.tif') for p in saved['recent_files'])


def test_load_folder_passes_app_config_folder_depth(tmp_path, monkeypatch) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    cfg.data.folder_depth = 7
    cfg.save()
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()

    captured: dict[str, object] = {}

    def _load_safe(path: str, *, kind, **kwargs):
        captured.update(kwargs)
        obj = AcqImageList.__new__(AcqImageList)
        obj.path = str(Path(path).resolve(strict=False))
        obj.file_list = []
        obj._files = []
        obj._files_by_id = {}
        return LoadResult(acq_image_list=obj, warnings=())

    monkeypatch.setattr('cloudscope.controllers.load_save_controller.AcqImageList.load_safe', _load_safe)
    bus.publish(LoadPathIntent(path=str(tmp_path), kind=LoadPathKind.FOLDER))
    assert captured.get('folder_depth') == 7


def test_load_from_recent_does_not_reorder_file_recents(tmp_path, monkeypatch) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'cfg.json')
    fa = tmp_path / 'a.tif'
    fb = tmp_path / 'b.tif'
    fa.write_text('x', encoding='utf-8')
    fb.write_text('y', encoding='utf-8')
    cfg.push_recent_file(str(fa))
    cfg.push_recent_file(str(fb))
    cfg.save()
    order_before = list(cfg.get_recent_files())
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()
    fake_list = _FakeList([_FakeFile(str(fb))])

    def _load_safe(_path: str, *, kind: str, **_kwargs):
        return LoadResult(acq_image_list=fake_list, warnings=())

    monkeypatch.setattr('cloudscope.controllers.load_save_controller.AcqImageList.load_safe', _load_safe)
    bus.publish(LoadPathIntent(path=str(fb), kind=LoadPathKind.FILE, from_recent=True))
    assert cfg.get_recent_files() == order_before
    assert normalize_stored_path(cfg.get_last_path()) == normalize_stored_path(str(fb))


def test_load_not_from_recent_moves_file_to_end_of_recents(tmp_path, monkeypatch) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'cfg.json')
    fa = tmp_path / 'a.tif'
    fb = tmp_path / 'b.tif'
    fa.write_text('x', encoding='utf-8')
    fb.write_text('y', encoding='utf-8')
    cfg.push_recent_file(str(fa))
    cfg.push_recent_file(str(fb))
    cfg.save()
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()
    fake_list = _FakeList([_FakeFile(str(fa))])

    def _load_safe(_path: str, *, kind: str, **_kwargs):
        return LoadResult(acq_image_list=fake_list, warnings=())

    monkeypatch.setattr('cloudscope.controllers.load_save_controller.AcqImageList.load_safe', _load_safe)
    bus.publish(LoadPathIntent(path=str(fa), kind=LoadPathKind.FILE, from_recent=False))
    files = cfg.get_recent_files()
    assert len(files) == 2
    assert files[-1].endswith('a.tif')


def test_remove_recent_path_intent_removes_file_entry(tmp_path) -> None:
    fp = tmp_path / 'a.tif'
    fp.write_text('x', encoding='utf-8')
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'cfg.json')
    cfg.push_recent_file(str(fp))
    cfg.save()
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()
    bus.publish(RemoveRecentPathIntent(path=str(fp), kind=LoadPathKind.FILE))
    assert cfg.get_recent_files() == []


def test_from_recent_missing_folder_prunes_without_repush(tmp_path, monkeypatch) -> None:
    missing_dir = tmp_path / 'gone'
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'cfg.json')
    cfg.push_recent_folder(str(missing_dir))
    cfg.save()
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    controller.bind()

    def _load_safe(path: str, *, kind, **_kwargs):
        obj = AcqImageList.__new__(AcqImageList)
        obj.path = str(Path(path).resolve(strict=False))
        obj.file_list = []
        obj._files = []
        obj._files_by_id = {}
        wpath = normalize_stored_path(path)
        return LoadResult(
            acq_image_list=obj,
            warnings=(
                LoadWarning(message='Folder does not exist or is not a directory', path=wpath),
            ),
        )

    monkeypatch.setattr('cloudscope.controllers.load_save_controller.AcqImageList.load_safe', _load_safe)
    assert cfg.get_recent_folders()
    bus.publish(LoadPathIntent(path=str(missing_dir), kind=LoadPathKind.FOLDER, from_recent=True))
    assert cfg.get_recent_folders() == []


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
