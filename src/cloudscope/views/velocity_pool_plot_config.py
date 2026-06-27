"""Default NicePool plot configuration for the velocity pool view."""

from __future__ import annotations

from typing import Any

from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE

VELOCITY_POOL_INITIAL_PLOT_CONFIG: dict[str, Any] = {
    "layout": "1x1",
    "plot_states": [
        {
            "pre_filter": {
                "accept": PRE_FILTER_NONE,
                "channel": PRE_FILTER_NONE,
                "roi_id": PRE_FILTER_NONE,
            },
            "xcol": "grandparent",
            "ycol": "velocity_mean",
            "plot_type": "swarm",
            "group_col": "grandparent",
            "color_grouping": None,  # is "(none)" in gui
            "use_absolute_value": True,
            "use_remove_values": True,
            "remove_values_threshold": 4001.0,
        }
    ],
}
