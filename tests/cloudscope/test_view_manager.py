"""Tests for ``ViewManager``."""

from __future__ import annotations

import pytest

from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from cloudscope.views.view_manager import ViewManager


class FakeRoot:
    """Small stand-in for a NiceGUI element."""

    def __init__(self) -> None:
        self.visible = True

    def update(self) -> None:
        """No-op update."""


class FakeView(BaseView):
    """Fake managed view."""

    view_id = ViewId.METADATA

    def build(self, parent=None):
        """Build fake root."""
        self.root = FakeRoot()  # type: ignore[assignment]
        self.after_build()
        return self.root


class OtherFakeView(FakeView):
    """Second fake view."""

    view_id = ViewId.APP_CONFIG


def test_register_rejects_duplicate_view_id() -> None:
    """ViewManager should fail fast on duplicate ids."""
    manager = ViewManager()
    bus = EventBus()

    manager.register(FakeView(bus))

    with pytest.raises(ValueError):
        manager.register(FakeView(bus))


def test_show_only_supports_no_active_view() -> None:
    """show_only(None, candidates) should hide all candidates."""
    manager = ViewManager()
    bus = EventBus()
    first = FakeView(bus)
    second = OtherFakeView(bus)
    first.build()
    second.build()
    manager.register(first)
    manager.register(second)

    manager.show_only(None, [ViewId.METADATA, ViewId.APP_CONFIG])

    assert not first.is_visible
    assert not second.is_visible


def test_show_only_selects_one_candidate() -> None:
    """show_only should show selected candidate and hide siblings."""
    manager = ViewManager()
    bus = EventBus()
    first = FakeView(bus)
    second = OtherFakeView(bus)
    first.build()
    second.build()
    manager.register(first)
    manager.register(second)

    manager.show_only(ViewId.APP_CONFIG, [ViewId.METADATA, ViewId.APP_CONFIG])

    assert not first.is_visible
    assert second.is_visible
