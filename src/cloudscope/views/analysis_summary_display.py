"""Format and display flat analysis summary dictionaries in NiceGUI views."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from nicegui import ui

from acqstore.acq_image.analysis.model import RUN_SUMMARY_METADATA_KEYS, BaseAnalysis


def _format_summary_value(value: Any) -> str:
    """Format one summary value for display.

    Floats are rounded to three decimal places without trailing zeros.
    """
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (float, np.floating)):
        as_float = float(value)
        if math.isnan(as_float) or math.isinf(as_float):
            return str(as_float)
        return f"{round(as_float, 3):.3f}".rstrip("0").rstrip(".")
    return str(value)


def format_analysis_summary_lines(summary: dict[str, Any]) -> str:
    """Format a flat summary as one ``key: value`` line per entry.

    Run metadata keys are listed first when present, followed by remaining keys
    in their source order.

    Args:
        summary: Analysis summary dictionary.

    Returns:
        Multi-line text suitable for a pre-wrapped label.
    """
    metadata_keys = [key for key in RUN_SUMMARY_METADATA_KEYS if key in summary]
    remaining_keys = [key for key in summary if key not in RUN_SUMMARY_METADATA_KEYS]
    ordered_keys = metadata_keys + remaining_keys
    return "\n".join(f"{key}: {_format_summary_value(summary[key])}" for key in ordered_keys)


def build_analysis_summary_expansion(summary: dict[str, Any]) -> None:
    """Render a collapsed expansion containing formatted summary lines.

    Args:
        summary: Analysis summary dictionary.

    Returns:
        None.
    """
    with ui.expansion("Summary", value=False).classes("w-full"):
        ui.label(format_analysis_summary_lines(summary)).classes(
            "text-xs whitespace-pre-wrap font-mono w-full"
        )


def build_analysis_summary_expansion_for_analysis(analysis: BaseAnalysis) -> None:
    """Render a collapsed expansion from analysis-declared flat summary columns.

    Args:
        analysis: Completed analysis instance.

    Returns:
        None.
    """
    build_analysis_summary_expansion(analysis.get_summary_values())
