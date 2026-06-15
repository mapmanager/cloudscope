"""Helper functions for NicePool plotting and control defaults."""

from __future__ import annotations

import pandas as pd
from nicegui import ui

_NUMERIC_KINDS = {"i", "u", "f"}
_AGGRID_COMPACT_CSS_INJECTED = False


def numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return numeric column names from a DataFrame.

    Args:
        df: DataFrame to inspect.

    Returns:
        Numeric column names in DataFrame order.
    """
    return [str(column) for column in df.columns if getattr(df[column].dtype, "kind", None) in _NUMERIC_KINDS]


def categorical_candidates(df: pd.DataFrame) -> list[str]:
    """Return columns suitable for categorical grouping controls.

    Args:
        df: DataFrame to inspect.

    Returns:
        Candidate categorical columns.
    """
    out: list[str] = []
    row_count = len(df)
    for column in df.columns:
        series = df[column]
        kind = getattr(series.dtype, "kind", None)
        if kind in {"O", "b"} or str(series.dtype) == "category":
            out.append(str(column))
            continue
        unique_count = series.nunique(dropna=True)
        if row_count > 0 and unique_count <= max(20, int(0.05 * row_count)):
            out.append(str(column))
    return out


def is_categorical_column(df: pd.DataFrame, column: str) -> bool:
    """Return whether a column is a categorical candidate.

    Args:
        df: DataFrame to inspect.
        column: Column name.

    Returns:
        True when the column is a categorical candidate.
    """
    return column in categorical_candidates(df)


def ensure_aggrid_compact_css() -> None:
    """Inject compact AG Grid CSS once.

    Returns:
        None.
    """
    global _AGGRID_COMPACT_CSS_INJECTED
    if _AGGRID_COMPACT_CSS_INJECTED:
        return
    ui.add_head_html(
        """
        <style>
        .aggrid-compact .ag-cell,
        .aggrid-compact .ag-header-cell {
            padding: 2px 6px;
            font-size: 0.75rem;
            line-height: 1.2;
        }
        </style>
        """
    )
    _AGGRID_COMPACT_CSS_INJECTED = True
