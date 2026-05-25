"""Tests for the CloudScope home page controller."""

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.files import FileListChanged
from cloudscope.events.selection import (
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
    SelectChannelIntent,
    SelectFileIntent,
    SelectRoiIntent,
)


def test_load_demo_files_publishes_file_list_and_file_selection_only() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    published: list[object] = []
    event_bus.subscribe(FileListChanged, published.append)
    event_bus.subscribe(FileSelectionChanged, published.append)
    event_bus.subscribe(ChannelSelectionChanged, published.append)
    event_bus.subscribe(RoiSelectionChanged, published.append)

    controller.load_demo_files(['file-a', 'file-b'])

    assert len(published) == 2
    assert isinstance(published[0], FileListChanged)
    assert published[0].file_ids == ['file-a', 'file-b']
    assert isinstance(published[1], FileSelectionChanged)
    assert published[1].file_id == 'file-a'
    assert published[1].channel == 0
    assert published[1].roi_id is None
    assert published[1].acq_image is None


def test_select_file_resets_channel_and_roi() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a', 'file-b'])
    controller.state.selection.channel = 2
    controller.state.selection.roi_id = 1

    published: list[FileSelectionChanged] = []
    event_bus.subscribe(FileSelectionChanged, published.append)
    event_bus.publish(SelectFileIntent(file_id='file-b'))

    assert published[-1].file_id == 'file-b'
    assert published[-1].channel == 0
    assert published[-1].roi_id is None


def test_select_channel_and_roi_publish_narrow_state_events() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a'])

    channels: list[ChannelSelectionChanged] = []
    rois: list[RoiSelectionChanged] = []
    event_bus.subscribe(ChannelSelectionChanged, channels.append)
    event_bus.subscribe(RoiSelectionChanged, rois.append)

    event_bus.publish(SelectChannelIntent(channel=2))
    event_bus.publish(SelectRoiIntent(roi_id=2))

    assert len(channels) == 1
    assert channels[0].channel == 2
    assert len(rois) == 1
    assert rois[0].roi_id == 2
