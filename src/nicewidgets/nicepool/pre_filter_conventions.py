"""Pre-filter value conventions for NicePool."""

from __future__ import annotations

from typing import Any

PRE_FILTER_NONE = "(none)"


def default_pre_filter(columns: list[str] | tuple[str, ...]) -> dict[str, str]:
    """Return a no-filter selection for every pre-filter column.

    Args:
        columns: Pre-filter column names.

    Returns:
        Mapping from column name to ``PRE_FILTER_NONE``.
    """
    return {str(column): PRE_FILTER_NONE for column in columns}


def format_pre_filter_display(pre_filter: dict[str, Any]) -> str:
    """Format a pre-filter mapping for plot titles.

    Args:
        pre_filter: Mapping from column names to selected values.

    Returns:
        Human-readable filter description.
    """
    active = [f"{key}={value}" for key, value in pre_filter.items() if value not in (None, PRE_FILTER_NONE)]
    return ", ".join(active) if active else "all rows"
