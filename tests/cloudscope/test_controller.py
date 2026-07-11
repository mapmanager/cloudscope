"""Tests for the CloudScope home page controller."""

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.files import FileListChanged
from cloudscope.events.selection import (
    SELECTION_SOURCE_LOAD,
    SELECTION_SOURCE_VELOCITY_POOL,
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


def test_load_demo_files_marks_file_selection_source_as_load() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    published: list[FileSelectionChanged] = []
    event_bus.subscribe(FileSelectionChanged, published.append)

    controller.load_demo_files(['file-a'])

    assert published[-1].source == SELECTION_SOURCE_LOAD


def test_select_file_intent_source_propagates_to_state_event() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a', 'file-b'])

    published: list[FileSelectionChanged] = []
    event_bus.subscribe(FileSelectionChanged, published.append)
    event_bus.publish(
        SelectFileIntent(file_id='file-b', source=SELECTION_SOURCE_VELOCITY_POOL)
    )

    assert published[-1].file_id == 'file-b'
    assert published[-1].source == SELECTION_SOURCE_VELOCITY_POOL


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


def test_select_file_with_analysis_fields_propagates_through_state() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a'])

    published: list[FileSelectionChanged] = []
    event_bus.subscribe(FileSelectionChanged, published.append)

    event_bus.publish(
        SelectFileIntent(
            file_id='file-a',
            channel=2,
            roi_id=7,
            analysis_name='radon_velocity',
        )
    )

    assert published[-1].file_id == 'file-a'
    assert published[-1].channel == 2
    assert published[-1].roi_id == 7
    assert published[-1].analysis_name == 'radon_velocity'
    assert controller.state.selection.analysis_name == 'radon_velocity'


def test_select_channel_clears_analysis_name() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a'])
    event_bus.publish(
        SelectFileIntent(
            file_id='file-a',
            channel=1,
            roi_id=3,
            analysis_name='diameter',
        )
    )
    assert controller.state.selection.analysis_name == 'diameter'

    event_bus.publish(SelectChannelIntent(channel=2))

    assert controller.state.selection.analysis_name is None


def test_select_roi_clears_analysis_name() -> None:
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    controller.bind()
    controller.load_demo_files(['file-a'])
    event_bus.publish(
        SelectFileIntent(
            file_id='file-a',
            channel=1,
            roi_id=3,
            analysis_name='event',
        )
    )
    assert controller.state.selection.analysis_name == 'event'

    event_bus.publish(SelectRoiIntent(roi_id=9))

    assert controller.state.selection.analysis_name is None


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
