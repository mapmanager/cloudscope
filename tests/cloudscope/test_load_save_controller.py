"""Tests for load/save orchestration controller."""

from __future__ import annotations

import json
from pathlib import Path

from acqstore.acq_image.acq_image import parent_grandparent_folder_names
from acqstore.acq_image.acq_image_list import AcqImageList, LoadResult, LoadWarning
from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import TaskProgressChanged
from cloudscope.events.files import (
    LoadPathIntent,
    LoadPathKind,
    RecentPathsChanged,
    RemoveRecentPathIntent,
    SaveAllIntent,
    SaveSelectedIntent,
)
from cloudscope.events.status import AppStatusChanged
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

    def iter_save_all(self, *, should_cancel=None):
        total = len(self.get_dirty_files())
        completed = 0
        for item in self.get_dirty_files():
            if should_cancel is not None and should_cancel():
                from acqstore.acq_image.acq_image_list import SaveEvent, SaveProgress

                yield SaveProgress(event=SaveEvent.CANCELLED, completed=completed, total=total, file_id=item.file_id)
                return
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



def test_load_controller_cancels_matching_load_task(tmp_path) -> None:
    """CancelTaskIntent should cancel the active load task through TaskRunner."""
    from cloudscope.events.analysis import CancelTaskIntent, TaskKind

    class FakeRunner:
        def __init__(self) -> None:
            self.calls = []

        def cancel(self, *, task_kind=None, task_id=None):
            self.calls.append((task_kind, task_id))
            return True

    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    home = HomePageController(event_bus=bus)
    runner = FakeRunner()
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg, task_runner=runner)
    controller.bind()

    bus.publish(CancelTaskIntent(task_kind=TaskKind.LOAD, task_id='abc'))

    assert runner.calls == [(TaskKind.LOAD, 'abc')]


def test_save_all_uses_iter_save_all_cancel_callback(tmp_path) -> None:
    """Save-all worker should use AcqImageList cooperative save iteration."""
    from cloudscope.task_runner import TaskCancelled

    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg)
    files = _FakeList([_FakeFile('/tmp/a.tif', dirty=True), _FakeFile('/tmp/b.tif', dirty=True)])

    class CancelContext:
        def __init__(self) -> None:
            self.progress = []
            self.calls = 0

        def report_progress(self, fraction, message=''):
            self.progress.append((fraction, message))

        def is_cancelled(self):
            self.calls += 1
            return self.calls > 1

        def raise_if_cancelled(self):
            if self.is_cancelled():
                raise TaskCancelled('cancelled')

    context = CancelContext()

    try:
        controller._save_all_worker(files, context)
    except TaskCancelled:
        pass
    else:
        raise AssertionError('Expected TaskCancelled')

    assert files.get_files()[0].saved == 1
    assert files.get_files()[1].saved == 0


# ---- additional coverage tests ----


class _ImmediateTaskKindBus:
    """Minimal capture helper used across new tests."""

    def __init__(self, bus: EventBus) -> None:
        self.statuses: list[AppStatusChanged] = []
        self.progress: list[TaskProgressChanged] = []
        self.recents: list[RecentPathsChanged] = []
        bus.subscribe(AppStatusChanged, self.statuses.append)
        bus.subscribe(TaskProgressChanged, self.progress.append)
        bus.subscribe(RecentPathsChanged, self.recents.append)


def _build_controller(tmp_path, *, runner=None) -> tuple[LoadSaveController, EventBus, HomePageController, AppConfig, _ImmediateTaskKindBus]:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'cfg.json')
    home = HomePageController(event_bus=bus)
    controller = LoadSaveController(event_bus=bus, home_controller=home, app_config=cfg, task_runner=runner)
    controller.bind()
    cap = _ImmediateTaskKindBus(bus)
    return controller, bus, home, cfg, cap


# ---- _ImmediateTaskContext branches ----


def test_immediate_task_context_publishes_progress_with_unknown_fraction(tmp_path) -> None:
    """Progress with ``fraction=None`` should publish ``current=0``."""
    from cloudscope.controllers.load_save_controller import _ImmediateTaskContext
    from cloudscope.events.analysis import TaskKind

    bus = EventBus()
    cap = _ImmediateTaskKindBus(bus)
    ctx = _ImmediateTaskContext(
        task_kind=TaskKind.LOAD,
        task_id='abc',
        event_bus=bus,
        task_label='Load',
    )

    ctx.report_progress(None, 'starting')
    ctx.report_progress(0.5, 'half')

    assert cap.progress[0].current == 0
    assert cap.progress[1].current == 50
    assert ctx.is_cancelled() is False
    ctx.raise_if_cancelled()


# ---- _on_cancel_task additional branches ----


def test_cancel_task_ignored_for_analysis_kind(tmp_path) -> None:
    """Cancel for ANALYSIS kind is owned by AnalysisController; LoadSave must ignore it."""
    from cloudscope.events.analysis import CancelTaskIntent, TaskKind

    class FakeRunner:
        def __init__(self) -> None:
            self.cancel_called = False

        def cancel(self, *, task_kind=None, task_id=None):
            self.cancel_called = True
            return True

    runner = FakeRunner()
    _, bus, _, _, _ = _build_controller(tmp_path, runner=runner)

    bus.publish(CancelTaskIntent(task_kind=TaskKind.ANALYSIS))

    assert runner.cancel_called is False


def test_cancel_task_without_runner_publishes_warning(tmp_path) -> None:
    """A cancel intent for SAVE without a runner should publish a warning status."""
    from cloudscope.events.analysis import CancelTaskIntent, TaskKind

    _, bus, _, _, cap = _build_controller(tmp_path)

    bus.publish(CancelTaskIntent(task_kind=TaskKind.SAVE))

    assert cap.statuses[-1].level == 'warning'
    assert 'cancellable' in cap.statuses[-1].message.lower()


def test_cancel_task_publishes_warning_when_no_matching_task(tmp_path) -> None:
    """When the runner returns False, a warning status should be published."""
    from cloudscope.events.analysis import CancelTaskIntent, TaskKind

    class FakeRunner:
        def cancel(self, *, task_kind=None, task_id=None):
            return False

    _, bus, _, _, cap = _build_controller(tmp_path, runner=FakeRunner())
    cap.statuses.clear()
    bus.publish(CancelTaskIntent(task_kind=TaskKind.LOAD))

    assert cap.statuses
    assert 'matching' in cap.statuses[-1].message.lower()


# ---- _on_save_selected branches ----


def test_save_selected_warns_when_file_no_longer_exists(tmp_path) -> None:
    """SaveSelected should warn when the selected file_id is not in the list."""
    from cloudscope.state import PrimarySelection

    _, bus, home, _, cap = _build_controller(tmp_path)
    home.state.acq_image_list = _FakeList([_FakeFile('/tmp/a.tif', dirty=True)])
    home._state.selection = PrimarySelection(file_id='/does/not/exist.tif')
    cap.statuses.clear()

    bus.publish(SaveSelectedIntent())

    assert cap.statuses
    assert 'no longer exists' in cap.statuses[-1].message


def test_save_selected_info_when_not_dirty(tmp_path) -> None:
    """SaveSelected should INFO when the selected file has no unsaved changes."""
    from cloudscope.events.selection import SelectFileIntent

    _, bus, home, _, cap = _build_controller(tmp_path)
    home.bind()
    files = _FakeList([_FakeFile('/tmp/a.tif', dirty=False)])
    home.state.acq_image_list = files
    bus.publish(SelectFileIntent(file_id='/tmp/a.tif'))
    cap.statuses.clear()

    bus.publish(SaveSelectedIntent())

    assert cap.statuses[-1].level == 'info'
    assert 'no unsaved' in cap.statuses[-1].message.lower()


def test_save_selected_publishes_completion_status(tmp_path) -> None:
    """A successful save-selected should publish 'Saved selected file' INFO."""
    from cloudscope.events.selection import SelectFileIntent

    _, bus, home, _, cap = _build_controller(tmp_path)
    home.bind()
    files = _FakeList([_FakeFile('/tmp/a.tif', dirty=True)])
    home.state.acq_image_list = files
    bus.publish(SelectFileIntent(file_id='/tmp/a.tif'))
    cap.statuses.clear()
    cap.progress.clear()

    bus.publish(SaveSelectedIntent())

    assert any(s.message == 'Saved selected file' for s in cap.statuses)
    assert any(p.status == 'completed' for p in cap.progress)
    assert files.get_files()[0].saved == 1


def test_save_selected_failure_publishes_error(tmp_path) -> None:
    """If save() raises, an ERROR status should be published."""
    from cloudscope.events.selection import SelectFileIntent

    class _BoomFile(_FakeFile):
        def save(self) -> None:
            raise RuntimeError('disk full')

    _, bus, home, _, cap = _build_controller(tmp_path)
    home.bind()
    files = _FakeList([_BoomFile('/tmp/a.tif', dirty=True)])
    home.state.acq_image_list = files
    bus.publish(SelectFileIntent(file_id='/tmp/a.tif'))
    cap.statuses.clear()

    bus.publish(SaveSelectedIntent())

    assert any(s.level == 'error' and 'disk full' in s.message for s in cap.statuses)


# ---- _on_save_all branches ----


def test_save_all_no_list_warns(tmp_path) -> None:
    """SaveAll with no list loaded should warn 'No files loaded'."""
    _, bus, _, _, cap = _build_controller(tmp_path)

    bus.publish(SaveAllIntent())

    assert cap.statuses
    assert 'No files loaded' in cap.statuses[-1].message


def test_save_all_publishes_completion_status(tmp_path) -> None:
    """A successful save-all should publish 'Save all completed' INFO."""
    _, bus, home, _, cap = _build_controller(tmp_path)
    files = _FakeList(
        [_FakeFile('/tmp/a.tif', dirty=True), _FakeFile('/tmp/b.tif', dirty=True)]
    )
    home.state.acq_image_list = files
    cap.statuses.clear()

    bus.publish(SaveAllIntent())

    assert any(s.message == 'Save all completed' for s in cap.statuses)
    assert files.get_files()[0].saved == 1
    assert files.get_files()[1].saved == 1


def test_save_all_failure_publishes_error(tmp_path) -> None:
    """If iter_save_all raises, an ERROR status should be published."""

    class _BoomList(_FakeList):
        def iter_save_all(self, *, should_cancel=None):
            raise RuntimeError('iter boom')

    _, bus, home, _, cap = _build_controller(tmp_path)
    home.state.acq_image_list = _BoomList([_FakeFile('/tmp/a.tif', dirty=True)])
    cap.statuses.clear()

    bus.publish(SaveAllIntent())

    assert any(s.level == 'error' and 'iter boom' in s.message for s in cap.statuses)


# ---- _on_clear_recent_paths ----


def test_clear_recent_paths_clears_config_and_publishes(tmp_path) -> None:
    """ClearRecentPathsIntent should clear config and publish RecentPathsChanged + INFO."""
    from cloudscope.events.files import ClearRecentPathsIntent

    fp = tmp_path / 'a.tif'
    fp.write_text('x', encoding='utf-8')
    _, bus, _, cfg, cap = _build_controller(tmp_path)
    cfg.push_recent_file(str(fp))
    cfg.save()
    cap.statuses.clear()
    cap.recents.clear()

    bus.publish(ClearRecentPathsIntent())

    assert cfg.get_recent_files() == []
    assert cap.recents
    assert any(s.message == 'Cleared recent paths' for s in cap.statuses)


# ---- _recent_nominal_target_missing branches ----


def test_recent_nominal_target_missing_returns_false_for_unrelated_warning(tmp_path) -> None:
    """Warning paths different from the load path should not indicate staleness."""
    from cloudscope.controllers.load_save_controller import LoadSaveController

    result = LoadResult(
        acq_image_list=_FakeList([]),  # type: ignore[arg-type]
        warnings=(LoadWarning(message='Folder does not exist', path='/other/path'),),
    )

    assert (
        LoadSaveController._recent_nominal_target_missing(result, '/tmp/p', LoadPathKind.FOLDER)
        is False
    )


def test_recent_nominal_target_missing_returns_false_for_warning_without_path(tmp_path) -> None:
    """Warnings without a path attribute should not indicate staleness."""
    from cloudscope.controllers.load_save_controller import LoadSaveController

    result = LoadResult(
        acq_image_list=_FakeList([]),  # type: ignore[arg-type]
        warnings=(LoadWarning(message='Folder does not exist', path=None),),
    )

    assert (
        LoadSaveController._recent_nominal_target_missing(result, '/tmp/p', LoadPathKind.FOLDER)
        is False
    )


def test_recent_nominal_target_missing_returns_false_for_unrelated_message(tmp_path) -> None:
    """An unrelated warning message at the same path should not indicate staleness."""
    from cloudscope.controllers.load_save_controller import LoadSaveController

    path = '/tmp/p'
    result = LoadResult(
        acq_image_list=_FakeList([]),  # type: ignore[arg-type]
        warnings=(LoadWarning(message='unrelated', path=normalize_stored_path(path)),),
    )

    assert (
        LoadSaveController._recent_nominal_target_missing(result, path, LoadPathKind.FILE)
        is False
    )


# ---- _start_task fallback paths (no runner) ----


def test_start_task_sync_fallback_publishes_completed(tmp_path) -> None:
    """With no TaskRunner attached, _start_task runs worker synchronously and publishes COMPLETED."""
    from cloudscope.events.analysis import TaskKind

    controller, _, _, _, cap = _build_controller(tmp_path)
    calls = {'completed': False}

    controller._start_task(
        task_kind=TaskKind.LOAD,
        task_label='label',
        worker=lambda _ctx: 'result',
        on_completed=lambda r: calls.update(completed=(r == 'result')),
    )

    assert calls['completed'] is True
    assert any(p.status == 'completed' for p in cap.progress)


def test_start_task_sync_fallback_publishes_failed_on_exception(tmp_path) -> None:
    """Sync fallback should publish FAILED and call on_failed when worker raises."""
    from cloudscope.events.analysis import TaskKind

    controller, _, _, _, cap = _build_controller(tmp_path)
    captured: dict[str, object] = {}

    def _boom(_ctx):
        raise RuntimeError('boom')

    controller._start_task(
        task_kind=TaskKind.SAVE,
        task_label='label',
        worker=_boom,
        on_failed=lambda exc: captured.update(exc=str(exc)),
    )

    assert captured['exc'] == 'boom'
    assert any(p.status == 'failed' for p in cap.progress)


def test_start_task_sync_fallback_publishes_cancelled_on_taskcancelled(tmp_path) -> None:
    """Sync fallback should publish CANCELLED and call on_cancelled when worker raises TaskCancelled."""
    from cloudscope.events.analysis import TaskKind
    from cloudscope.task_runner import TaskCancelled

    controller, _, _, _, cap = _build_controller(tmp_path)
    captured = {'cancelled': False}

    def _cancel(_ctx):
        raise TaskCancelled('cancelled')

    controller._start_task(
        task_kind=TaskKind.SAVE,
        task_label='label',
        worker=_cancel,
        on_cancelled=lambda: captured.update(cancelled=True),
    )

    assert captured['cancelled'] is True
    assert any(p.status == 'cancelled' for p in cap.progress)


def test_load_path_worker_translates_load_cancelled_to_taskcancelled(tmp_path, monkeypatch) -> None:
    """A LoadCancelled raised inside AcqImageList.load_safe must surface as TaskCancelled."""
    from acqstore.acq_image.acq_image_list import LoadCancelled
    from cloudscope.task_runner import TaskCancelled

    controller, _, _, _, _ = _build_controller(tmp_path)

    def _raise_cancelled(*_args, **_kwargs):
        raise LoadCancelled('user cancelled')

    monkeypatch.setattr(
        'cloudscope.controllers.load_save_controller.AcqImageList.load_safe',
        _raise_cancelled,
    )

    import pytest

    with pytest.raises(TaskCancelled, match='user cancelled'):
        controller._load_path_worker(
            LoadPathIntent(path='/tmp/x', kind=LoadPathKind.FILE),
            _ImmediateContext(),
        )


def test_load_path_worker_reports_progress_with_known_total(tmp_path, monkeypatch) -> None:
    """The worker should turn (completed, total) callbacks into fractions."""
    controller, _, _, _, _ = _build_controller(tmp_path)
    captured: list[tuple[float | None, str]] = []

    class _Ctx:
        def report_progress(self, fraction, message=''):
            captured.append((fraction, message))

        def is_cancelled(self):
            return False

    def _load_safe(*_args, progress_callback=None, **_kwargs):
        if progress_callback is not None:
            progress_callback(0, 0, 'no total')
            progress_callback(1, 4, 'quarter')
            progress_callback(4, 4, 'done')
        return LoadResult(acq_image_list=_FakeList([]), warnings=())  # type: ignore[arg-type]

    monkeypatch.setattr(
        'cloudscope.controllers.load_save_controller.AcqImageList.load_safe', _load_safe
    )
    controller._load_path_worker(
        LoadPathIntent(path='/tmp/x', kind=LoadPathKind.FILE),
        _Ctx(),
    )

    assert captured[0][0] is None
    assert captured[1][0] == 0.25
    assert captured[2][0] == 1.0


class _ImmediateContext:
    """Tiny synchronous context for direct worker tests."""

    def report_progress(self, fraction, message=''):
        _ = fraction, message

    def is_cancelled(self):
        return False

    def raise_if_cancelled(self):
        return None
