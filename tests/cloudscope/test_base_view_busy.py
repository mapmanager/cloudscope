"""Tests for BaseView busy disable behavior."""

from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AppBusyChanged, TaskKind
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


class FakeRoot:
    """Fake NiceGUI root element."""

    def __init__(self) -> None:
        self.visible = True
        self.enabled = True
        self.updated = 0

    def classes(self, *, add: str | None = None, remove: str | None = None) -> None:
        """Record class mutation compatibility with NiceGUI root."""
        _ = add
        _ = remove

    def update(self) -> None:
        """Record update calls."""
        self.updated += 1


class FakeView(BaseView):
    """Concrete test view."""

    view_id = ViewId.METADATA

    def build(self, parent=None):
        """Build fake root."""
        self.root = FakeRoot()  # type: ignore[assignment]
        self.after_build()
        return self.root


def test_base_view_disables_on_app_busy() -> None:
    """Visible views should disable their root while app is busy."""
    bus = EventBus()
    view = FakeView(event_bus=bus)
    view.build()

    bus.publish(AppBusyChanged(is_busy=True, task_kind=TaskKind.ANALYSIS, task_id="1", message="busy"))

    assert not view.is_enabled

    bus.publish(AppBusyChanged(is_busy=False, task_kind=None, task_id=None, message="done"))

    assert view.is_enabled


class NeverDisabledView(FakeView):
    """View that remains enabled during busy tasks."""

    disable_when_busy = False


def test_base_view_can_opt_out_of_busy_disable() -> None:
    """Views can opt out of busy disabling."""
    bus = EventBus()
    view = NeverDisabledView(event_bus=bus)
    view.build()

    bus.publish(AppBusyChanged(is_busy=True, task_kind=TaskKind.ANALYSIS, task_id="1", message="busy"))

    assert view.is_enabled


def test_base_view_calls_enabled_changed_hook() -> None:
    """Busy-state disabling should notify subclasses after state changes."""

    class HookView(FakeView):
        """Fake view recording enabled hook calls."""

        def __init__(self, event_bus: EventBus) -> None:
            super().__init__(event_bus=event_bus)
            self.enabled_calls: list[bool] = []

        def on_enabled_changed(self, enabled: bool) -> None:
            """Record enabled state."""
            self.enabled_calls.append(enabled)

    bus = EventBus()
    view = HookView(event_bus=bus)
    view.build()

    bus.publish(AppBusyChanged(is_busy=True, task_kind=TaskKind.ANALYSIS, task_id="1", message="busy"))
    bus.publish(AppBusyChanged(is_busy=False, task_kind=None, task_id=None, message="done"))

    assert view.enabled_calls[-2:] == [False, True]
