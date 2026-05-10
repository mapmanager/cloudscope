"""Data models for the NiceWidgets ECharts line-plot widget."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class EChartLineData:
    """One line series for an ECharts value/value plot.

    Args:
        x: X-axis values in data coordinates.
        y: Y-axis values in data coordinates.
        x_label: Human-readable x-axis label.
        y_label: Human-readable y-axis label.
        series_name: Human-readable series name.
    """

    x: tuple[float, ...]
    y: tuple[float, ...]
    x_label: str
    y_label: str
    series_name: str = "series"

    @classmethod
    def from_sequences(
        cls,
        *,
        x: Sequence[float],
        y: Sequence[float],
        x_label: str,
        y_label: str,
        series_name: str = "series",
    ) -> "EChartLineData":
        """Create line data from numeric sequences.

        Args:
            x: X-axis values.
            y: Y-axis values.
            x_label: Human-readable x-axis label.
            y_label: Human-readable y-axis label.
            series_name: Human-readable series name.

        Returns:
            Immutable line-data object.

        Raises:
            ValueError: If x and y lengths differ.
        """
        x_values = tuple(float(value) for value in x)
        y_values = tuple(float(value) for value in y)
        if len(x_values) != len(y_values):
            raise ValueError(
                f"x and y must have the same length, got {len(x_values)} and {len(y_values)}"
            )
        return cls(
            x=x_values,
            y=y_values,
            x_label=str(x_label),
            y_label=str(y_label),
            series_name=str(series_name),
        )


@dataclass(frozen=True, slots=True)
class EChartAxisRange:
    """Optional x-axis range for an ECharts value axis.

    Args:
        x_min: Minimum x-axis value, or None for auto.
        x_max: Maximum x-axis value, or None for auto.
    """

    x_min: float | None = None
    x_max: float | None = None

    def __post_init__(self) -> None:
        """Validate axis range.

        Raises:
            ValueError: If both bounds are set and x_min >= x_max.
        """
        if self.x_min is not None and self.x_max is not None and self.x_min >= self.x_max:
            raise ValueError(f"x_min ({self.x_min}) must be less than x_max ({self.x_max})")
