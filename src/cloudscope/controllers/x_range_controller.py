"""Controller for app-level x-axis range sync between primary raster and 1D plot.

Responsibilities:

* Translate :class:`SetPrimaryXRangeIntent` into a mutation on
  ``home_controller.state.primary_x_range`` and publish
  :class:`PrimaryXRangeChanged`.
* Reset the x-range on :class:`FileSelectionChanged` **only** when the file id
  actually transitions (skip channel-only changes, ROI-only changes, and the
  no-op re-publish that happens on initial list load with the same id).
* Dedup: never publish a state event when the new value equals the current
  state, which short-circuits the producer/consumer echo loop.
"""

from __future__ import annotations

import math

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.selection import FileSelectionChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent
from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

_X_RANGE_EPS = 1e-9


def _values_equal(a: float | None, b: float | None) -> bool:
    """Return whether two optional floats are equal within a small tolerance.

    ``None`` (auto) is treated as a distinct value, equal only to itself.

    Args:
        a: First value.
        b: Second value.

    Returns:
        ``True`` when both are ``None`` or both are finite and close.
    """
    if a is None or b is None:
        return a is None and b is None
    if not (math.isfinite(a) and math.isfinite(b)):
        return False
    return abs(a - b) <= _X_RANGE_EPS


def _ranges_equal(
    current: tuple[float | None, float | None],
    new: tuple[float | None, float | None],
) -> bool:
    """Compare two ``(x_min, x_max)`` tuples allowing ``None``."""
    return _values_equal(current[0], new[0]) and _values_equal(current[1], new[1])


class XRangeController:
    """Bind x-range intents and selection events to ``HomePageState.primary_x_range``.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: Controller owning the home page state.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        home_controller: HomePageController,
    ) -> None:
        self._event_bus = event_bus
        self._home_controller = home_controller
        self._last_file_id: str | None = None

    def bind(self) -> None:
        """Subscribe to x-range and file-selection events.

        Returns:
            None.
        """
        self._event_bus.subscribe(SetPrimaryXRangeIntent, self._on_set_intent)
        self._event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        # Initial baseline: whatever HomePageState already reports.
        self._last_file_id = self._home_controller.state.selection.file_id

    def _normalize(
        self,
        x_min: float | None,
        x_max: float | None,
    ) -> tuple[float | None, float | None]:
        """Normalize an x-range pair.

        Swaps inverted bounds. ``(None, None)`` is preserved verbatim. A
        partial ``(value, None)`` or ``(None, value)`` is preserved verbatim
        (callers may need to express "auto on one end" in future); current
        consumers always pass either both or neither.

        Args:
            x_min: Requested minimum.
            x_max: Requested maximum.

        Returns:
            Normalized pair.
        """
        if x_min is None or x_max is None:
            return x_min, x_max
        lo, hi = float(x_min), float(x_max)
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi

    def _publish_if_changed(self, new_range: tuple[float | None, float | None]) -> None:
        """Update state and publish exactly once when the new value differs.

        Args:
            new_range: Candidate new ``(x_min, x_max)``.

        Returns:
            None.
        """
        state = self._home_controller.state
        if _ranges_equal(state.primary_x_range, new_range):
            return
        state.primary_x_range = new_range
        self._event_bus.publish(
            PrimaryXRangeChanged(x_min=new_range[0], x_max=new_range[1])
        )

    def _on_set_intent(self, intent: SetPrimaryXRangeIntent) -> None:
        """Apply a user-driven x-range change.

        Args:
            intent: Incoming intent from a producer view.

        Returns:
            None.
        """
        new_range = self._normalize(intent.x_min, intent.x_max)
        self._publish_if_changed(new_range)

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        """Reset the x-range to auto when the file id actually transitions.

        Channel switches within the same file do not reach this handler (they
        come through ``ChannelSelectionChanged``, which this controller does
        not subscribe to).

        Args:
            event: Selection state event.

        Returns:
            None.
        """
        prev = self._last_file_id
        self._last_file_id = event.file_id
        if event.file_id == prev:
            return
        self._publish_if_changed((None, None))
