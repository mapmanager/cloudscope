"""Tests for :class:`XRangeController`."""

from __future__ import annotations

from cloudscope.controllers.home_page_controller import HomePageController, HomePageState
from cloudscope.controllers.x_range_controller import XRangeController
from cloudscope.event_bus import EventBus
from cloudscope.events.selection import FileSelectionChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent
from cloudscope.state import PrimarySelection


def _make() -> tuple[EventBus, HomePageController, XRangeController, list[PrimaryXRangeChanged]]:
    """Build a wired controller and a captured-state-events list."""
    bus = EventBus()
    home = HomePageController(
        bus,
        initial_state=HomePageState(
            file_ids=[],
            selection=PrimarySelection(),
            acq_image_list=None,
        ),
    )
    ctrl = XRangeController(event_bus=bus, home_controller=home)
    ctrl.bind()
    seen: list[PrimaryXRangeChanged] = []
    bus.subscribe(PrimaryXRangeChanged, seen.append)
    return bus, home, ctrl, seen


def test_intent_publishes_changed_and_updates_state() -> None:
    """Happy path: intent -> state mutation -> PrimaryXRangeChanged."""
    bus, home, _, seen = _make()
    bus.publish(SetPrimaryXRangeIntent(x_min=1.5, x_max=4.5))
    assert home.state.primary_x_range == (1.5, 4.5)
    assert seen == [PrimaryXRangeChanged(x_min=1.5, x_max=4.5)]


def test_inverted_range_is_swapped_before_publish() -> None:
    """Controller normalizes inverted ``(x_min, x_max)`` pairs."""
    bus, home, _, seen = _make()
    bus.publish(SetPrimaryXRangeIntent(x_min=9.0, x_max=2.0))
    assert home.state.primary_x_range == (2.0, 9.0)
    assert seen == [PrimaryXRangeChanged(x_min=2.0, x_max=9.0)]


def test_duplicate_intent_does_not_republish() -> None:
    """Echo dedup: a second identical intent must not republish."""
    bus, _, _, seen = _make()
    bus.publish(SetPrimaryXRangeIntent(x_min=1.0, x_max=2.0))
    bus.publish(SetPrimaryXRangeIntent(x_min=1.0, x_max=2.0))
    assert len(seen) == 1


def test_near_duplicate_intent_within_tolerance_is_deduped() -> None:
    """Tiny float deltas (Plotly echo-style) are treated as duplicates."""
    bus, _, _, seen = _make()
    bus.publish(SetPrimaryXRangeIntent(x_min=1.0, x_max=2.0))
    bus.publish(SetPrimaryXRangeIntent(x_min=1.0 + 1e-12, x_max=2.0 - 1e-12))
    assert len(seen) == 1


def test_auto_none_intent_publishes_when_state_was_finite() -> None:
    """Resetting to auto from a finite state publishes a single event."""
    bus, home, _, seen = _make()
    bus.publish(SetPrimaryXRangeIntent(x_min=1.0, x_max=2.0))
    bus.publish(SetPrimaryXRangeIntent(x_min=None, x_max=None))
    assert home.state.primary_x_range == (None, None)
    assert seen[-1] == PrimaryXRangeChanged(x_min=None, x_max=None)
    assert len(seen) == 2


def test_file_change_to_different_id_resets_x_range_to_auto() -> None:
    """Switching files publishes a single auto-range reset."""
    bus, home, _, seen = _make()
    bus.publish(SetPrimaryXRangeIntent(x_min=1.0, x_max=2.0))
    seen.clear()
    bus.publish(
        FileSelectionChanged(file_id='other', acq_image=None, channel=0, roi_id=None)
    )
    assert home.state.primary_x_range == (None, None)
    assert seen == [PrimaryXRangeChanged(x_min=None, x_max=None)]


def test_file_change_to_same_id_does_not_reset() -> None:
    """No-op file events (same id) preserve the current x-range."""
    bus, home, _, seen = _make()
    bus.publish(FileSelectionChanged(file_id='a', acq_image=None, channel=0, roi_id=None))
    seen.clear()
    bus.publish(SetPrimaryXRangeIntent(x_min=1.0, x_max=2.0))
    bus.publish(FileSelectionChanged(file_id='a', acq_image=None, channel=0, roi_id=None))
    assert home.state.primary_x_range == (1.0, 2.0)
    assert seen == [PrimaryXRangeChanged(x_min=1.0, x_max=2.0)]


def test_channel_change_does_not_affect_x_range() -> None:
    """``ChannelSelectionChanged`` is not subscribed -> x-range preserved."""
    from cloudscope.events.selection import ChannelSelectionChanged

    bus, home, _, seen = _make()
    bus.publish(SetPrimaryXRangeIntent(x_min=3.0, x_max=7.0))
    seen.clear()
    bus.publish(ChannelSelectionChanged(channel=1))
    assert home.state.primary_x_range == (3.0, 7.0)
    assert seen == []
