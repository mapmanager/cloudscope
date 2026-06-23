"""Tests for :class:`ImagePixelsController`."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from cloudscope.controllers.image_pixels_controller import ImagePixelsController


class _FakeAcqImage:
    """Minimal stand-in for :class:`AcqImage` pixel-load orchestration tests."""

    def __init__(self, *, loaded: bool = False) -> None:
        self._loaded = loaded
        self.load_calls = 0

    def pixels_loaded(self) -> bool:
        return self._loaded

    def load_image_data(self) -> None:
        self.load_calls += 1
        self._loaded = True


def test_clear_selection_invokes_callback_synchronously() -> None:
    ctrl = ImagePixelsController()
    seen: list[str] = []
    ctrl.ensure_loaded(None, None, on_complete=lambda: seen.append('done'))
    assert seen == ['done']


def test_demo_file_without_acq_image_invokes_callback_without_load() -> None:
    ctrl = ImagePixelsController()
    seen: list[str] = []
    ctrl.ensure_loaded('demo.tif', None, on_complete=lambda: seen.append('done'))
    assert seen == ['done']


def test_already_loaded_file_invokes_callback_synchronously() -> None:
    ctrl = ImagePixelsController()
    acq = _FakeAcqImage(loaded=True)
    seen: list[str] = []
    ctrl.ensure_loaded('a.oir', acq, on_complete=lambda: seen.append('done'))
    assert acq.load_calls == 0
    assert seen == ['done']


def test_same_file_reselection_from_pool_invokes_without_reload() -> None:
    ctrl = ImagePixelsController()
    acq = _FakeAcqImage(loaded=True)
    seen: list[str] = []
    ctrl.ensure_loaded('a.oir', acq, on_complete=lambda: seen.append('first'))
    ctrl.ensure_loaded('a.oir', acq, on_complete=lambda: seen.append('second'))
    assert acq.load_calls == 0
    assert seen == ['first', 'second']


def test_cold_file_schedules_io_bound_load_then_invokes_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctrl = ImagePixelsController()
    acq = _FakeAcqImage(loaded=False)
    pending_tasks: list[asyncio.Task[None]] = []
    seen: list[str] = []

    async def _fake_io_bound(fn, *args, **kwargs):
        fn(*args, **kwargs)
        await asyncio.sleep(0)

    def _capture_schedule(coro):
        pending_tasks.append(asyncio.create_task(coro))

    monkeypatch.setattr(
        'cloudscope.controllers.image_pixels_controller.run.io_bound',
        _fake_io_bound,
    )
    monkeypatch.setattr(
        'cloudscope.controllers.image_pixels_controller._schedule_coro',
        _capture_schedule,
    )

    async def _run() -> None:
        ctrl.ensure_loaded('a.oir', acq, on_complete=lambda: seen.append('done'))
        await asyncio.gather(*pending_tasks)
        assert acq.load_calls == 1
        assert seen == ['done']

    asyncio.run(_run())


def test_stale_load_is_ignored_after_fast_file_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    ctrl = ImagePixelsController()
    acq_a = _FakeAcqImage(loaded=False)
    acq_b = _FakeAcqImage(loaded=False)
    pending: dict[str, asyncio.Event] = {'a': asyncio.Event(), 'b': asyncio.Event()}
    pending_tasks: list[asyncio.Task[None]] = []
    seen: list[str] = []

    async def _fake_io_bound(fn, *args, **kwargs):
        owner = getattr(fn, '__self__', None)
        if owner is acq_a:
            await pending['a'].wait()
        fn(*args, **kwargs)
        await asyncio.sleep(0)

    def _capture_schedule(coro):
        pending_tasks.append(asyncio.create_task(coro))

    monkeypatch.setattr(
        'cloudscope.controllers.image_pixels_controller.run.io_bound',
        _fake_io_bound,
    )
    monkeypatch.setattr(
        'cloudscope.controllers.image_pixels_controller._schedule_coro',
        _capture_schedule,
    )

    async def _run() -> None:
        ctrl.ensure_loaded('a.oir', acq_a, on_complete=lambda: seen.append('a'))
        task_a = pending_tasks[0]
        ctrl.ensure_loaded('b.oir', acq_b, on_complete=lambda: seen.append('b'))
        task_b = pending_tasks[1]
        await asyncio.gather(task_b)
        assert acq_b.load_calls == 1
        assert seen == ['b']

        pending['a'].set()
        await asyncio.gather(task_a)
        assert acq_a.load_calls == 1
        assert seen == ['b']

    asyncio.run(_run())


def test_load_failure_does_not_invoke_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    ctrl = ImagePixelsController()
    acq = _FakeAcqImage(loaded=False)
    pending_tasks: list[asyncio.Task[None]] = []
    seen: list[str] = []

    def _boom() -> None:
        raise OSError('disk read failed')

    acq.load_image_data = MagicMock(side_effect=_boom)  # type: ignore[method-assign]

    async def _fake_io_bound(fn, *args, **kwargs):
        fn(*args, **kwargs)

    def _capture_schedule(coro):
        pending_tasks.append(asyncio.create_task(coro))

    monkeypatch.setattr(
        'cloudscope.controllers.image_pixels_controller.run.io_bound',
        _fake_io_bound,
    )
    monkeypatch.setattr(
        'cloudscope.controllers.image_pixels_controller._schedule_coro',
        _capture_schedule,
    )

    async def _run() -> None:
        ctrl.ensure_loaded('a.oir', acq, on_complete=lambda: seen.append('done'))
        await asyncio.gather(*pending_tasks, return_exceptions=True)
        assert seen == []

    asyncio.run(_run())
