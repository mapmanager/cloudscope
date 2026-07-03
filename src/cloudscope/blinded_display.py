"""Display-only masking helpers for CloudScope blinded analysis mode."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from acqstore.acq_image.metadata import EXPERIMENT_METADATA_SCHEMA
from acqstore.acq_image.tree_rows import (
    ACQ_TREE_ROW_ID_FIELD,
    ACQ_TREE_ROW_TYPE_ANALYSIS,
    ACQ_TREE_ROW_TYPE_FIELD,
)

BLINDED_VALUE = "Blinded"
"""Replacement text for revealing categorical display values."""

_IDENTITY_DISPLAY_COLUMNS = ("name",)
_FOLDER_DISPLAY_COLUMNS = ("parent", "grandparent")
_METADATA_DISPLAY_COLUMNS = tuple(field.name for field in EXPERIMENT_METADATA_SCHEMA.fields)


@dataclass(frozen=True, slots=True)
class PoolSelectionIdentity:
    """Real selection identity hidden behind one blinded pool display row."""

    file_id: str
    channel: int | None
    roi_id: int | None


@dataclass(frozen=True, slots=True)
class PoolDisplayFrame:
    """Masked pool DataFrame plus row-id maps for GUI selection sync."""

    dataframe: pd.DataFrame
    display_to_real_selection: dict[str, PoolSelectionIdentity]
    real_to_display_row_id: dict[str, str]


def build_file_label_map(file_ids: Iterable[str]) -> dict[str, str]:
    """Return stable blinded labels for file identifiers in display order.

    Args:
        file_ids: File identifiers in the order shown to the user.

    Returns:
        Mapping from real file identifier to labels such as ``"File 1"``.
    """
    labels: dict[str, str] = {}
    for file_id in file_ids:
        key = str(file_id)
        if key not in labels:
            labels[key] = f"File {len(labels) + 1}"
    return labels


def build_file_label_map_from_state(app_state: object | None) -> dict[str, str]:
    """Return blinded file labels from a CloudScope app-state object.

    Args:
        app_state: Home-page state carrying either ``acq_image_list`` or
            ``file_ids``. ``None`` produces an empty mapping.

    Returns:
        Real file id to blinded display label mapping.
    """
    if app_state is None:
        return {}
    acq_image_list = getattr(app_state, "acq_image_list", None)
    if acq_image_list is not None:
        get_files = getattr(acq_image_list, "get_files", None)
        if callable(get_files):
            return build_file_label_map(str(acq_file.file_id) for acq_file in get_files())
    file_ids = getattr(app_state, "file_ids", None)
    if file_ids is not None:
        return build_file_label_map(str(file_id) for file_id in file_ids)
    return {}


def display_file_name(
    file_id: str | None,
    *,
    blinded: bool,
    file_label_map: Mapping[str, str] | None = None,
) -> str:
    """Return a display file name for the current blinded state.

    Args:
        file_id: Real file identifier, usually a path.
        blinded: Whether to return an anonymous label.
        file_label_map: Optional real file id to anonymous label mapping.

    Returns:
        Basename for unblinded display, or an anonymous ``"File N"`` label.
    """
    if file_id is None:
        return ""
    file_id_text = str(file_id)
    if not blinded:
        return str(Path(file_id_text).name)
    labels = file_label_map or {}
    return labels.get(file_id_text, BLINDED_VALUE)


def mask_file_list_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    file_label_map: Mapping[str, str],
) -> list[dict[str, object]]:
    """Return masked copies of flat file-list rows.

    Args:
        rows: Source file-list rows.
        file_label_map: Real file id to anonymous label mapping.

    Returns:
        New row dictionaries with revealing display fields masked.
    """
    return [_mask_file_display_row(row, file_label_map=file_label_map) for row in rows]


def mask_tree_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    file_label_map: Mapping[str, str],
) -> list[dict[str, object]]:
    """Return masked copies of file-list tree rows.

    Analysis child rows keep their analysis names and identity fields because
    they are not file identity or experimental metadata.

    Args:
        rows: Source tree rows.
        file_label_map: Real file id to anonymous label mapping.

    Returns:
        New row dictionaries with revealing file-row display fields masked.
    """
    masked: list[dict[str, object]] = []
    for row in rows:
        if row.get(ACQ_TREE_ROW_TYPE_FIELD) == ACQ_TREE_ROW_TYPE_ANALYSIS:
            masked.append(dict(row))
        else:
            masked.append(_mask_file_display_row(row, file_label_map=file_label_map))
    return masked


def mask_pool_dataframe(
    df: pd.DataFrame,
    *,
    file_label_map: Mapping[str, str],
) -> PoolDisplayFrame:
    """Return a masked display DataFrame for ``NicePool``.

    The returned DataFrame is safe to hand to the GUI for bias-reduction
    display. It masks file names, path-like display columns, folder names, and
    experiment metadata while preserving numeric analysis values. The original
    backend DataFrame is not mutated.

    Args:
        df: Backend analysis-pool DataFrame.
        file_label_map: Real file id to anonymous label mapping.

    Returns:
        Masked DataFrame and row-id mappings used by ``VelocityPoolView`` to
        translate GUI selection back to real CloudScope selections.
    """
    if df.empty:
        return PoolDisplayFrame(
            dataframe=df.copy(),
            display_to_real_selection={},
            real_to_display_row_id={},
        )

    labels = dict(file_label_map)
    out = df.copy()
    display_to_real_selection: dict[str, PoolSelectionIdentity] = {}
    real_to_display_row_id: dict[str, str] = {}
    _prepare_pool_display_columns(out)

    for index, row in df.iterrows():
        file_id = _string_or_empty(row.get("path"))
        if file_id and file_id not in labels:
            labels[file_id] = f"File {len(labels) + 1}"
        file_label = labels.get(file_id, BLINDED_VALUE)
        display_row_id = f"{file_label}|pool_row={index}"
        real_row_id = _string_or_empty(row.get("pool_row_id"))
        channel = _optional_int(row.get("channel"))
        roi_id = _optional_int(row.get("roi_id"))

        if "pool_row_id" in out.columns:
            out.at[index, "pool_row_id"] = display_row_id
        for column in ("name", "path"):
            if column in out.columns:
                out.at[index, column] = file_label
        for column in _FOLDER_DISPLAY_COLUMNS + _METADATA_DISPLAY_COLUMNS:
            if column in out.columns:
                out.at[index, column] = BLINDED_VALUE

        display_to_real_selection[display_row_id] = PoolSelectionIdentity(
            file_id=file_id,
            channel=channel,
            roi_id=roi_id,
        )
        if real_row_id:
            real_to_display_row_id[real_row_id] = display_row_id

    return PoolDisplayFrame(
        dataframe=out,
        display_to_real_selection=display_to_real_selection,
        real_to_display_row_id=real_to_display_row_id,
    )


def _mask_file_display_row(
    row: Mapping[str, object],
    *,
    file_label_map: Mapping[str, str],
) -> dict[str, object]:
    out = dict(row)
    file_id = _row_file_id(out)
    label = display_file_name(file_id, blinded=True, file_label_map=file_label_map)
    for column in _IDENTITY_DISPLAY_COLUMNS:
        if column in out:
            out[column] = label
    for column in _FOLDER_DISPLAY_COLUMNS + _METADATA_DISPLAY_COLUMNS:
        if column in out:
            out[column] = BLINDED_VALUE
    return out


def _prepare_pool_display_columns(df: pd.DataFrame) -> None:
    """Allow blinded string labels in display-only pool columns."""
    display_columns = (
        "pool_row_id",
        "name",
        "path",
        *_FOLDER_DISPLAY_COLUMNS,
        *_METADATA_DISPLAY_COLUMNS,
    )
    for column in display_columns:
        if column in df.columns:
            df[column] = df[column].astype("object")


def _row_file_id(row: Mapping[str, object]) -> str | None:
    for key in ("path", "file_id", ACQ_TREE_ROW_ID_FIELD):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _string_or_empty(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return int(value)
