"""Display options for the ECharts widget."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EChartDisplayOptions:
    """User-facing display toggles for :class:`EChartWidget`.

    Args:
        show_toolbar: Whether ECharts' toolbox (zoom/restore/brush icons) is
            visible above the chart. Defaults to ``False`` so the chart starts
            uncluttered; users can toggle it via the right-click context menu.
        show_hover_info: Whether the ECharts ``tooltip`` floating layer (hover
            label with x/y values) is shown. Maps to ECharts' ``tooltip.show``
            option. Defaults to ``False`` so the chart starts uncluttered;
            users can toggle it via the right-click context menu.
    """

    show_toolbar: bool = False
    show_hover_info: bool = False
