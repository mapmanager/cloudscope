"""Headless tests for the NicePool DataFrame helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from nicewidgets.nicepool.config import NicePoolConfig, resolve_pre_filter_columns
from nicewidgets.nicepool.dataframe_adapter import dataframe_to_rows, filter_dataframe, unique_filter_values
from nicewidgets.nicepool.nice_pool import NicePool


def test_resolve_pre_filter_columns_auto_detects_common_columns() -> None:
    """Common filter columns should be detected when present."""
    cols = ("pool_row_id", "accept", "channel", "roi_id", "velocity_mean")

    assert resolve_pre_filter_columns(cols) == ("accept", "channel", "roi_id")


def test_resolve_pre_filter_columns_respects_explicit_order() -> None:
    """Explicit filter columns should preserve caller order and skip missing."""
    cols = ("pool_row_id", "channel", "roi_id")

    assert resolve_pre_filter_columns(cols, explicit_columns=("roi_id", "missing", "channel")) == (
        "roi_id",
        "channel",
    )


def test_dataframe_to_rows_requires_unique_stringable_ids() -> None:
    """Row conversion should validate the unique row-id contract."""
    df = pd.DataFrame(
        [
            {"pool_row_id": "a", "value": 1.0},
            {"pool_row_id": "b", "value": float("nan")},
        ]
    )

    rows = dataframe_to_rows(df, unique_row_id_col="pool_row_id")

    assert rows == [{"pool_row_id": "a", "value": 1.0}, {"pool_row_id": "b", "value": None}]


def test_dataframe_to_rows_rejects_duplicates() -> None:
    """Duplicate row ids should fail fast."""
    df = pd.DataFrame([{"pool_row_id": "a"}, {"pool_row_id": "a"}])

    with pytest.raises(ValueError, match="Duplicate row id"):
        dataframe_to_rows(df, unique_row_id_col="pool_row_id")


def test_filter_dataframe_uses_string_values() -> None:
    """Filters should match display string values for numeric categories."""
    df = pd.DataFrame(
        [
            {"pool_row_id": "a", "channel": 0, "roi_id": 1},
            {"pool_row_id": "b", "channel": 1, "roi_id": 1},
        ]
    )

    filtered = filter_dataframe(df, {"channel": "1"})

    assert filtered["pool_row_id"].tolist() == ["b"]


def test_unique_filter_values_are_sorted_strings() -> None:
    """Unique filter values should be sorted strings for select options."""
    df = pd.DataFrame([{"channel": 2}, {"channel": 0}, {"channel": 2}])

    assert unique_filter_values(df, ("channel",)) == {"channel": ["0", "2"]}


def test_nicepool_init_auto_detects_filters() -> None:
    """NicePool should expose auto-detected filter columns without building UI."""
    df = pd.DataFrame([{"pool_row_id": "a", "accept": True, "channel": 0, "roi_id": 1}])

    widget = NicePool(df, config=NicePoolConfig(unique_row_id_col="pool_row_id"))

    assert widget.pre_filter_columns == ("accept", "channel", "roi_id")
