"""Tests for application theme events and Plotly image-view consumers."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.events.base import StateEvent
from cloudscope.events.theme import ThemeChanged
from cloudscope.views.primary_image_view import PrimaryImageView
from cloudscope.views.reference_image_view import ReferenceImageView


class _FakeViewer:
    """Small PlotlyRasterViewer stand-in for theme event tests."""

    def __init__(self) -> None:
        """Create an empty fake viewer."""
        self.dark_mode_values: list[bool] = []

    def set_dark_mode(self, enabled: bool) -> None:
        """Record a dark-mode update.

        Args:
            enabled: Dark-mode state sent by the view.

        Returns:
            None.
        """
        self.dark_mode_values.append(enabled)


def test_theme_changed_is_state_event() -> None:
    """ThemeChanged should be a state event consumed by views."""
    event = ThemeChanged(dark_mode=True)

    assert isinstance(event, StateEvent)
    assert event.dark_mode is True


def test_primary_image_view_initializes_plotly_theme_from_dark_mode() -> None:
    """Primary image view should pass initial dark-mode state into the raster viewer."""
    view = PrimaryImageView(EventBus(), dark_mode=True)

    assert view._viewer._display_options.theme == 'dark'


def test_reference_image_view_initializes_plotly_theme_from_dark_mode() -> None:
    """Reference image view should pass initial dark-mode state into the raster viewer."""
    view = ReferenceImageView(EventBus(), dark_mode=True)

    assert view._viewer._display_options.theme == 'dark'


def test_primary_image_view_consumes_theme_changed_event() -> None:
    """Primary image view should route ThemeChanged to its Plotly raster viewer."""
    event_bus = EventBus()
    view = PrimaryImageView(event_bus)
    fake_viewer = _FakeViewer()
    view._viewer = fake_viewer

    view.subscribe_events()
    event_bus.publish(ThemeChanged(dark_mode=True))

    assert fake_viewer.dark_mode_values == [True]


def test_reference_image_view_consumes_theme_changed_event() -> None:
    """Reference image view should route ThemeChanged to its Plotly raster viewer."""
    event_bus = EventBus()
    view = ReferenceImageView(event_bus)
    fake_viewer = _FakeViewer()
    view._viewer = fake_viewer

    view.subscribe_events()
    event_bus.publish(ThemeChanged(dark_mode=False))

    assert fake_viewer.dark_mode_values == [False]


def test_primary_image_view_refresh_syncs_theme_provider() -> None:
    """Primary image view should resync theme when shown after missing events."""
    view = PrimaryImageView(EventBus(), dark_mode_provider=lambda: True)
    fake_viewer = _FakeViewer()
    view._viewer = fake_viewer
    view._refresh_raster_from_current_selection = lambda: None

    view.refresh_from_state()

    assert fake_viewer.dark_mode_values == [True]


def test_reference_image_view_refresh_syncs_theme_provider() -> None:
    """Reference image view should resync theme when shown after missing events."""
    view = ReferenceImageView(EventBus(), dark_mode_provider=lambda: True)
    fake_viewer = _FakeViewer()
    view._viewer = fake_viewer
    view._refresh_reference_from_current_selection = lambda *, force: None

    view.refresh_from_state()

    assert fake_viewer.dark_mode_values == [True]
