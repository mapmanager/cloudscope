"""Tests for the CloudScope home page controller."""

from cloudscope.core.controller import HomePageController
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import FileListChanged, PrimarySelectionChanged, SelectChannelIntent, SelectFileIntent, SelectRoiIntent


def test_load_demo_files_publishes_file_list_and_selection() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    published: list[object] = []
    event_bus.subscribe(FileListChanged, published.append)
    event_bus.subscribe(PrimarySelectionChanged, published.append)

    controller.load_demo_files(['file-a', 'file-b'])

    assert isinstance(published[0], FileListChanged)
    assert published[0].file_ids == ['file-a', 'file-b']
    assert isinstance(published[1], PrimarySelectionChanged)
    assert published[1].file_id == 'file-a'
    assert published[1].channel == 0
    assert published[1].roi_id is None


def test_select_file_resets_channel_and_roi() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a', 'file-b'])
    controller.state.selection.channel = 2
    controller.state.selection.roi_id = 'roi-1'

    published: list[PrimarySelectionChanged] = []
    event_bus.subscribe(PrimarySelectionChanged, published.append)
    event_bus.publish(SelectFileIntent(file_id='file-b'))

    assert published[-1].file_id == 'file-b'
    assert published[-1].channel == 0
    assert published[-1].roi_id is None


def test_select_channel_and_roi_publish_state_changes() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a'])

    published: list[PrimarySelectionChanged] = []
    event_bus.subscribe(PrimarySelectionChanged, published.append)

    event_bus.publish(SelectChannelIntent(channel=2))
    event_bus.publish(SelectRoiIntent(roi_id='roi-2'))

    assert published[0].channel == 2
    assert published[1].roi_id == 'roi-2'
