"""Tests for ``BaseView`` lifecycle behavior."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.event_bus import EventBus
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


@dataclass(frozen=True)
class TestEvent:
    """Test event."""


class FakeRoot:
    """Small stand-in for a NiceGUI element."""

    def __init__(self) -> None:
        self.visible = True
        self.update_count = 0

    def update(self) -> None:
        """Record update calls."""
        self.update_count += 1


class FakeView(BaseView):
    """Fake view that subscribes while visible."""

    view_id = ViewId.METADATA

    def __init__(self, event_bus: EventBus, *, initially_visible: bool = True) -> None:
        super().__init__(event_bus=event_bus, initially_visible=initially_visible)
        self.events: list[TestEvent] = []
        self.refresh_count = 0

    def build(self, parent=None):
        """Build fake root."""
        self.root = FakeRoot()  # type: ignore[assignment]
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to test events."""
        self.add_subscription(self.event_bus.subscribe(TestEvent, self.events.append))

    def refresh_from_state(self) -> None:
        """Record refresh calls."""
        self.refresh_count += 1


def test_visible_view_subscribes_after_build() -> None:
    """Initially visible views should subscribe and refresh after build."""
    bus = EventBus()
    view = FakeView(bus)

    view.build()
    bus.publish(TestEvent())

    assert len(view.events) == 1
    assert view.refresh_count == 1


def test_hidden_view_does_not_consume_events_until_shown() -> None:
    """Initially hidden views should not consume events until shown."""
    bus = EventBus()
    view = FakeView(bus, initially_visible=False)

    view.build()
    bus.publish(TestEvent())
    view.show()
    bus.publish(TestEvent())

    assert len(view.events) == 1
    assert view.refresh_count == 1


def test_hide_unsubscribes_from_events() -> None:
    """Hiding a view should unsubscribe its event handlers."""
    bus = EventBus()
    view = FakeView(bus)

    view.build()
    view.hide()
    bus.publish(TestEvent())

    assert view.events == []
    assert view.root is not None
    assert view.root.visible is False

from cloudscope.events.selection import ChannelSelectionChanged, FileSelectionChanged, RoiSelectionChanged


def test_base_view_tracks_primary_selection_for_all_views() -> None:
    """BaseView should cache file/channel/ROI selection while visible."""
    bus = EventBus()
    view = FakeView(bus)
    view.build()

    bus.publish(FileSelectionChanged(file_id="/tmp/a.oir", acq_image="image", channel=0, roi_id=1))
    bus.publish(ChannelSelectionChanged(channel=2))
    bus.publish(RoiSelectionChanged(roi_id=3))

    assert view.current_selection.file_id == "/tmp/a.oir"
    assert view.current_selection.channel == 2
    assert view.current_selection.roi_id == 3
    assert view.current_acq_image == "image"


class FakeAcqImage:
    """Fake acquisition image."""

    def __init__(self, file_id: str) -> None:
        self.file_id = file_id


class FakeAcqImageList:
    """Fake acquisition image list."""

    def __init__(self, image: FakeAcqImage) -> None:
        self.image = image

    def get_file_by_id(self, file_id: str):
        """Return image when ids match."""
        if file_id == self.image.file_id:
            return self.image
        return None


class FakeAppState:
    """Fake app state with selection and file list."""

    def __init__(self) -> None:
        self.selection = PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1)
        self.acq_image_list = FakeAcqImageList(FakeAcqImage("/tmp/a.oir"))


def test_base_view_backend_access_helpers() -> None:
    """BaseView should expose common app-state lookup helpers."""
    bus = EventBus()
    state = FakeAppState()
    view = FakeView(bus)
    view.app_state = state

    assert view.get_acq_image_list() is state.acq_image_list
    assert view.get_acq_image_by_file_id("/tmp/a.oir") is state.acq_image_list.image
    assert view.get_acq_image_by_file_id("/tmp/missing.oir") is None

    view.current_selection = state.selection
    assert view.get_selected_acq_image() is state.acq_image_list.image
    assert view.has_valid_primary_selection() is True


def test_selected_acq_image_is_dirty_reads_known_acqimage_api() -> None:
    """BaseView should read ``AcqImage.is_dirty`` directly when selected."""

    class DirtyImage:
        """Fake selected AcqImage with a known dirty API."""

        is_dirty = True

    bus = EventBus()
    view = FakeView(bus)
    view.current_acq_image = DirtyImage()

    assert view.selected_acq_image_is_dirty() is True


def test_selected_acq_image_is_dirty_false_without_selection() -> None:
    """BaseView should report clean state when no AcqImage is selected."""
    bus = EventBus()
    view = FakeView(bus)

    assert view.selected_acq_image_is_dirty() is False


class _FakeLabel:
    """Minimal stand-in for ``ui.label`` used by selection-label tests."""

    def __init__(self) -> None:
        self.text = ""


def test_refresh_selection_label_no_op_when_label_not_built() -> None:
    """``refresh_selection_label`` should no-op before ``build_selection_label``."""
    bus = EventBus()
    view = FakeView(bus)
    view.current_selection = PrimarySelection(
        file_id="/abs/path/sample.oir", channel=0, roi_id=1
    )

    view.refresh_selection_label()

    assert not hasattr(view, "_selection_label")


def test_refresh_selection_label_displays_no_file_when_unset() -> None:
    """``refresh_selection_label`` should render single placeholder line."""
    bus = EventBus()
    view = FakeView(bus)
    view._selection_label = _FakeLabel()  # type: ignore[attr-defined]

    view.refresh_selection_label()

    assert view._selection_label.text == "No file selected"  # type: ignore[attr-defined]


def test_refresh_selection_label_renders_three_lines_with_basename() -> None:
    """Full selection should render basename, channel, and roi on three lines."""
    bus = EventBus()
    view = FakeView(bus)
    view._selection_label = _FakeLabel()  # type: ignore[attr-defined]
    view.current_selection = PrimarySelection(
        file_id="/abs/path/to/sample.oir", channel=2, roi_id=5
    )

    view.refresh_selection_label()

    lines = view._selection_label.text.split("\n")  # type: ignore[attr-defined]
    assert lines == ["file: sample.oir", "channel: 2", "roi: 5"]


def test_refresh_selection_label_uses_em_dash_for_missing_channel_and_roi() -> None:
    """Partial selection should still render three lines with em-dash placeholders."""
    bus = EventBus()
    view = FakeView(bus)
    view._selection_label = _FakeLabel()  # type: ignore[attr-defined]
    view.current_selection = PrimarySelection(
        file_id="/abs/path/sample.oir", channel=None, roi_id=None
    )

    view.refresh_selection_label()

    lines = view._selection_label.text.split("\n")  # type: ignore[attr-defined]
    assert lines == ["file: sample.oir", "channel: —", "roi: —"]


def test_refresh_selection_label_uses_em_dash_only_for_missing_field() -> None:
    """Channel set but ROI unset should render dash only on the ROI line."""
    bus = EventBus()
    view = FakeView(bus)
    view._selection_label = _FakeLabel()  # type: ignore[attr-defined]
    view.current_selection = PrimarySelection(
        file_id="/abs/path/sample.oir", channel=0, roi_id=None
    )

    view.refresh_selection_label()

    lines = view._selection_label.text.split("\n")  # type: ignore[attr-defined]
    assert lines == ["file: sample.oir", "channel: 0", "roi: —"]
