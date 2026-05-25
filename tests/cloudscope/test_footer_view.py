"""Tests for ``FooterView`` and footer display helpers."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.events.selection import (
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
)
from cloudscope.views.footer_view import FooterView, footer_display_values

# Same placeholder as the view module (em dash).
_DASH = "—"


class _TextSink:
    """Minimal stand-in for ``ui.label`` with a ``text`` attribute."""

    def __init__(self) -> None:
        self.text = ""


def test_footer_display_values_no_file_forces_all_placeholders() -> None:
    assert footer_display_values(None, 0, 1) == (_DASH, _DASH, _DASH)


def test_footer_display_values_basename_and_placeholders() -> None:
    assert footer_display_values("/tmp/data/sample.oir", None, None) == (
        "sample.oir",
        _DASH,
        _DASH,
    )


def test_footer_display_values_simple_file_id_uses_path_name() -> None:
    """Non-path ids still go through ``Path(...).name`` (identity for simple names)."""
    assert footer_display_values("file-a", 0, None) == ("file-a", "0", _DASH)


def test_footer_display_values_all_set() -> None:
    assert footer_display_values("/x/y.z", 2, 7) == ("y.z", "2", "7")


def test_footer_view_reacts_to_file_then_channel_and_roi() -> None:
    """View handlers update label text without calling ``build()`` (no NiceGUI slot)."""
    bus = EventBus()
    view = FooterView(bus)
    view.on_show()
    view._file_label = _TextSink()
    view._channel_label = _TextSink()
    view._roi_label = _TextSink()

    bus.publish(
        FileSelectionChanged(
            file_id="/data/image.oir",
            acq_image=None,
            channel=0,
            roi_id=None,
        )
    )
    assert view._file_label.text == "File: image.oir"
    assert view._channel_label.text == "Channel: 0"
    assert view._roi_label.text == f"ROI: {_DASH}"

    bus.publish(ChannelSelectionChanged(channel=2))
    assert view._channel_label.text == "Channel: 2"

    bus.publish(RoiSelectionChanged(roi_id=5))
    assert view._roi_label.text == "ROI: 5"


def test_footer_view_clear_file_resets_display_to_placeholders() -> None:
    bus = EventBus()
    view = FooterView(bus)
    view.on_show()
    view._file_label = _TextSink()
    view._channel_label = _TextSink()
    view._roi_label = _TextSink()

    bus.publish(
        FileSelectionChanged(
            file_id="/a/b.oir",
            acq_image=None,
            channel=1,
            roi_id=2,
        )
    )
    bus.publish(FileSelectionChanged(file_id=None, acq_image=None, channel=None, roi_id=None))
    assert view._file_label.text == f"File: {_DASH}"
    assert view._channel_label.text == f"Channel: {_DASH}"
    assert view._roi_label.text == f"ROI: {_DASH}"
