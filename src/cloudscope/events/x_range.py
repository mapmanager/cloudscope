"""App-level x-axis range sync between the primary raster and the 1D plot.

The producers are :class:`PlotlyRasterViewer` (pan/zoom on the Plotly heatmap)
and :class:`PlotlyPlotWidget` (acq analysis plot via ``AcqAnalysisPlotView``).
The x-axis is shared because the Plotly heatmap's plot-x dimension and the 1D
analysis trace's x-axis are in the same physical units and share an origin.

Reset semantics: the controller subscribes to :class:`FileSelectionChanged`
and resets the x-range to ``(None, None)`` (auto) on file transitions only.
``ChannelSelectionChanged`` is intentionally ignored because channels of one
``AcqImage`` share the same image shape and physical calibration; preserving
the x-range across channel switches matches what users expect when they pan
or zoom in to inspect a feature and then cycle channels to compare.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cloudscope.events.base import IntentEvent, StateEvent

_X_RANGE_EPS = 1e-9


def x_ranges_equal(
    a: tuple[float | None, float | None],
    b: tuple[float | None, float | None],
) -> bool:
    """Return whether two ``(x_min, x_max)`` pairs are equal within tolerance.

    ``None`` (auto) is equal only to itself.

    Args:
        a: First range pair.
        b: Second range pair.

    Returns:
        ``True`` when both bounds match within tolerance or are both auto.
    """
    for av, bv in zip(a, b, strict=True):
        if av is None or bv is None:
            if av is not bv:
                return False
            continue
        if not (math.isfinite(av) and math.isfinite(bv)):
            return False
        if abs(av - bv) > _X_RANGE_EPS:
            return False
    return True


@dataclass(frozen=True)
class SetPrimaryXRangeIntent(IntentEvent):
    """Request a change to the primary x-axis range.

    ``None`` for either bound means "auto" (reset to the full x extent).
    Both producers may emit this; the controller dedups before publishing
    a state change.

    Args:
        x_min: New minimum x value, or ``None`` for auto.
        x_max: New maximum x value, or ``None`` for auto.
    """

    x_min: float | None
    x_max: float | None


@dataclass(frozen=True)
class PrimaryXRangeChanged(StateEvent):
    """Authoritative x-axis range state after the controller mutated it.

    Args:
        x_min: Current minimum x value, or ``None`` for auto.
        x_max: Current maximum x value, or ``None`` for auto.
    """

    x_min: float | None
    x_max: float | None
