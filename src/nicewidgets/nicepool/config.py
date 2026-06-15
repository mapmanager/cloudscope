"""Configuration helpers for the reusable NicePool widget.

``nicewidgets.nicepool`` is a general-purpose DataFrame widget layer. It does
not know about CloudScope, AcqImageList, or analysis models. The config object
keeps the widget contract explicit while allowing CloudScope and scripts to
share the same DataFrame-driven UI component.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


DEFAULT_AUTO_PRE_FILTER_COLUMNS: tuple[str, ...] = ("accept", "channel", "roi_id")


@dataclass(frozen=True, slots=True)
class NicePoolConfig:
    """Configuration for a DataFrame-backed NicePool widget.

    Args:
        unique_row_id_col: Column containing stable row identifiers.
        pre_filter_columns: Explicit categorical columns to expose as pre-filter
            controls. Missing columns are ignored.
        auto_pre_filter_columns: Candidate columns that are auto-detected when
            ``pre_filter_columns`` is None.
        table_font_size_px: Optional AG Grid table font size.
    """

    unique_row_id_col: str = "pool_row_id"
    pre_filter_columns: Sequence[str] | None = None
    auto_pre_filter_columns: Sequence[str] = field(default_factory=lambda: DEFAULT_AUTO_PRE_FILTER_COLUMNS)
    table_font_size_px: int | None = None


def resolve_pre_filter_columns(
    available_columns: Sequence[str],
    *,
    explicit_columns: Sequence[str] | None = None,
    auto_columns: Sequence[str] = DEFAULT_AUTO_PRE_FILTER_COLUMNS,
) -> tuple[str, ...]:
    """Return pre-filter columns present in a DataFrame schema.

    Args:
        available_columns: DataFrame column names.
        explicit_columns: Caller-provided columns. When omitted, auto-detected
            conventional columns are used.
        auto_columns: Candidate columns for auto-detection.

    Returns:
        Tuple of column names that exist in ``available_columns``.
    """
    available = {str(column) for column in available_columns}
    candidates = explicit_columns if explicit_columns is not None else auto_columns
    return tuple(str(column) for column in candidates if str(column) in available)
