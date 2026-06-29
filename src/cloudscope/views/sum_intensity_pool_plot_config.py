"""Default NicePool plot configuration for the sum-intensity peaks pool tab."""

from __future__ import annotations

from typing import Any

from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE

SUM_INTENSITY_POOL_INITIAL_PLOT_CONFIG: dict[str, Any] = {
    "layout": "1x1",
    "plot_states": [
        {
            "pre_filter": {
                "accept": PRE_FILTER_NONE,
                "channel": PRE_FILTER_NONE,
                "roi_id": PRE_FILTER_NONE,
                "peak_row_type": "peak",
            },
            "xcol": "grandparent",
            "ycol": "peak_amplitude",
            "plot_type": "swarm",
            "group_col": "grandparent",
            "color_grouping": None,
            "use_absolute_value": False,
            "use_remove_values": False,
        }
    ],
}
