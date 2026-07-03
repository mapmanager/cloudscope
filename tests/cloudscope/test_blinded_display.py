"""Tests for CloudScope blinded-analysis display helpers."""

from __future__ import annotations

import pandas as pd

from acqstore.acq_image.tree_rows import (
    ACQ_TREE_ROW_ID_FIELD,
    ACQ_TREE_ROW_TYPE_ANALYSIS,
    ACQ_TREE_ROW_TYPE_FIELD,
    ACQ_TREE_ROW_TYPE_FILE,
)
from cloudscope.blinded_display import (
    BLINDED_VALUE,
    build_file_label_map,
    mask_pool_dataframe,
    mask_tree_rows,
)


def test_build_file_label_map_uses_display_order() -> None:
    labels = build_file_label_map(["/data/a.oir", "/data/b.oir"])

    assert labels == {"/data/a.oir": "File 1", "/data/b.oir": "File 2"}


def test_mask_tree_rows_masks_file_rows_but_preserves_identity() -> None:
    rows = [
        {
            ACQ_TREE_ROW_ID_FIELD: "/data/a.oir",
            ACQ_TREE_ROW_TYPE_FIELD: ACQ_TREE_ROW_TYPE_FILE,
            "path": "/data/a.oir",
            "name": "a.oir",
            "parent": "condition-a",
            "grandparent": "genotype-a",
            "condition": "treated",
            "genotype": "wt",
        },
        {
            ACQ_TREE_ROW_ID_FIELD: "/data/a.oir|analysis",
            ACQ_TREE_ROW_TYPE_FIELD: ACQ_TREE_ROW_TYPE_ANALYSIS,
            "name": "radon_velocity",
        },
    ]

    masked = mask_tree_rows(rows, file_label_map={"/data/a.oir": "File 1"})

    assert masked[0][ACQ_TREE_ROW_ID_FIELD] == "/data/a.oir"
    assert masked[0]["path"] == "/data/a.oir"
    assert masked[0]["name"] == "File 1"
    assert masked[0]["parent"] == BLINDED_VALUE
    assert masked[0]["grandparent"] == BLINDED_VALUE
    assert masked[0]["condition"] == BLINDED_VALUE
    assert masked[0]["genotype"] == BLINDED_VALUE
    assert masked[1]["name"] == "radon_velocity"


def test_mask_pool_dataframe_masks_display_values_and_keeps_selection_map() -> None:
    df = pd.DataFrame(
        [
            {
                "pool_row_id": "/data/a.oir|channel=0|roi_id=1",
                "name": "a.oir",
                "path": "/data/a.oir",
                "parent": "parent-a",
                "grandparent": "grand-a",
                "condition": "treated",
                "genotype": "wt",
                "channel": 0,
                "roi_id": 1,
                "velocity_mean": 12.5,
            }
        ]
    )

    display = mask_pool_dataframe(df, file_label_map={"/data/a.oir": "File 1"})
    row = display.dataframe.iloc[0]
    display_row_id = str(row["pool_row_id"])

    assert row["name"] == "File 1"
    assert row["path"] == "File 1"
    assert row["parent"] == BLINDED_VALUE
    assert row["grandparent"] == BLINDED_VALUE
    assert row["condition"] == BLINDED_VALUE
    assert row["genotype"] == BLINDED_VALUE
    assert row["velocity_mean"] == 12.5
    assert "/data/a.oir" not in display_row_id
    assert display.display_to_real_selection[display_row_id].file_id == "/data/a.oir"
    assert display.real_to_display_row_id["/data/a.oir|channel=0|roi_id=1"] == display_row_id


def test_mask_pool_dataframe_handles_nullable_numeric_metadata_columns() -> None:
    """Blinded strings should be valid for display-only numeric metadata columns."""
    df = pd.DataFrame(
        {
            "pool_row_id": pd.Series(["/data/a.oir|channel=0|roi_id=1"], dtype="object"),
            "name": pd.Series(["a.oir"], dtype="object"),
            "path": pd.Series(["/data/a.oir"], dtype="object"),
            "parent": pd.Series(["parent-a"], dtype="object"),
            "grandparent": pd.Series(["grand-a"], dtype="object"),
            "depth": pd.Series([125.0], dtype="Float64"),
            "branch_order": pd.Series([2], dtype="Int64"),
            "channel": pd.Series([0], dtype="Int64"),
            "roi_id": pd.Series([1], dtype="Int64"),
            "velocity_mean": pd.Series([12.5], dtype="Float64"),
        }
    )

    display = mask_pool_dataframe(df, file_label_map={"/data/a.oir": "File 1"})
    row = display.dataframe.iloc[0]

    assert row["depth"] == BLINDED_VALUE
    assert row["branch_order"] == BLINDED_VALUE
    assert row["velocity_mean"] == 12.5
    assert str(display.dataframe["velocity_mean"].dtype) == "Float64"
    assert display.display_to_real_selection[str(row["pool_row_id"])].file_id == "/data/a.oir"
