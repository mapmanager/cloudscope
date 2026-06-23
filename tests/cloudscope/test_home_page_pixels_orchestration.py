"""Integration tests for HomePage pixel-load orchestration."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.controllers.image_pixels_controller import ImagePixelsController
from cloudscope.event_bus import EventBus
from cloudscope.events.selection import FileSelectionChanged, SelectFileIntent
from cloudscope.state import PrimarySelection


class _FakeAcqImage:
    """Minimal stand-in for backend pixel-load orchestration."""

    file_id = 'a.oir'

    def __init__(self, *, loaded: bool = False) -> None:
        self._loaded = loaded
        self.load_calls = 0

    def pixels_loaded(self) -> bool:
        return self._loaded

    def load_image_data(self) -> None:
        self.load_calls += 1
        self._loaded = True

    def get_default_channel(self) -> int:
        return 0

    def get_default_roi(self) -> int | None:
        return None


def test_clear_selection_publishes_immediately() -> None:
    bus = EventBus()
    pixels = ImagePixelsController()
    home = HomePageController(event_bus=bus, image_pixels_controller=pixels)
    home.bind()
    home.load_demo_files(['file-a'])

    seen: list[FileSelectionChanged] = []
    bus.subscribe(FileSelectionChanged, seen.append)
    seen.clear()

    bus.publish(SelectFileIntent(file_id=None))

    assert len(seen) == 1
    assert seen[0].file_id is None


def test_cold_file_defers_file_selection_until_pixels_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = EventBus()
    pixels = ImagePixelsController()
    home = HomePageController(event_bus=bus, image_pixels_controller=pixels)
    home.bind()

    acq = _FakeAcqImage(loaded=False)
    acq_list = MagicMock()
    acq_list.get_file_by_id.return_value = acq
    home.state.acq_image_list = acq_list
    home.state.file_ids = ['a.oir']
    home.state.selection = PrimarySelection(file_id='a.oir', channel=0)

    seen: list[FileSelectionChanged] = []
    bus.subscribe(FileSelectionChanged, seen.append)

    pending_tasks: list[asyncio.Task[None]] = []

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
        bus.publish(SelectFileIntent(file_id='a.oir'))
        assert seen == []
        await asyncio.gather(*pending_tasks)
        assert acq.load_calls == 1
        assert len(seen) == 1
        assert seen[0].file_id == 'a.oir'
        assert seen[0].acq_image is acq

    asyncio.run(_run())
