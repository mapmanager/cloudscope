"""Plot summary models for NicePool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlotSummary:
    """Small summary produced alongside a Plotly figure.

    Args:
        plot_type: Plot type string.
        row_count: Number of rows used for the plot.
        details: Additional summary values.
    """

    plot_type: str
    row_count: int
    details: dict[str, Any] = field(default_factory=dict)


def format_plot_summary_to_str(summary: PlotSummary) -> str:
    """Format a plot summary for clipboard or status display.

    Args:
        summary: Plot summary.

    Returns:
        Multi-line summary string.
    """
    parts = [f"plot_type: {summary.plot_type}", f"row_count: {summary.row_count}"]
    parts.extend(f"{key}: {value}" for key, value in summary.details.items())
    return "\n".join(parts)
