"""Base DataFrame pool for collection-level analysis summaries.

Analysis pools live in ``acqstore`` because they are backend data-model objects,
not GUI widgets. They provide a scripting-friendly, flat pandas DataFrame with
one row per acquisition image/channel/ROI selection and one scalar value per
column. CloudScope can consume the same DataFrame at runtime without knowing
analysis-specific sidecar details.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from acqstore.acq_image.analysis.model import AnalysisKey, BaseAnalysis

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage
    from acqstore.acq_image.acq_image_list import AcqImageList


class AnalysisPool:
    """Flat summary table owned by an ``AcqImageList``.

    ``AnalysisPool`` is the base class for concrete collection-level tables such
    as ``VelocityAnalysisPool``. It owns the DataFrame, row identity, row
    refresh/removal behavior, and CSV export. Derived classes define which
    analysis types contribute summary columns.

    The pool does not run analysis and is not a persistence source of truth. It
    reflects state already present in each ``AcqImage`` analysis set, especially
    small JSON summary payloads that are inexpensive to load for large file
    collections.

    Args:
        acq_image_list: Collection that owns this pool.
    """

    base_columns: tuple[str, ...] = (
        "pool_row_id",
        "pool_row",
        "name",
        "path",
        "parent",
        "grandparent",
        "condition",
        "genotype",
        "accept",
        "channel",
        "roi_id",
        "step_y",
        "step_x",
    )
    analysis_specs: tuple[tuple[str, type[BaseAnalysis]], ...] = ()

    def __init__(self, acq_image_list: AcqImageList) -> None:
        self._acq_image_list = acq_image_list
        self._df = pd.DataFrame(columns=self.columns)
        self.rebuild()

    @property
    def columns(self) -> tuple[str, ...]:
        """Return the complete pool column schema.

        Returns:
            Tuple containing base columns followed by prefixed analysis summary
            columns.
        """
        columns = list(self.base_columns)
        for prefix, analysis_cls in self.analysis_specs:
            columns.extend(
                f"{prefix}_{column}" for column in analysis_cls.get_summary_columns()
            )
        return tuple(columns)

    @property
    def dataframe(self) -> pd.DataFrame:
        """Return the live pool DataFrame.

        Returns:
            The internal DataFrame object. Mutating it directly is possible but
            callers that need isolation should use :meth:`get_dataframe`.
        """
        return self._df

    def get_dataframe(self, *, copy: bool = True) -> pd.DataFrame:
        """Return the pool DataFrame.

        Args:
            copy: When true, return a copy so caller mutations do not affect the
                pool. When false, return the live DataFrame.

        Returns:
            Pool DataFrame with one row per ``(file, channel, roi_id)``.
        """
        if copy:
            return self._df.copy()
        return self._df

    def rebuild(self) -> None:
        """Rebuild the entire pool from the current ``AcqImageList`` state.

        Returns:
            None.
        """
        rows: list[dict[str, object]] = []
        for acq_image in self._acq_image_list.get_files():
            for channel, roi_id in self._iter_selection_keys(acq_image):
                rows.append(self._build_row(acq_image, channel=channel, roi_id=roi_id))
        self._df = pd.DataFrame(rows, columns=self.columns)
        self._reset_display_row_numbers()

    def refresh_row(self, file_id: str, *, channel: int, roi_id: int) -> None:
        """Create or replace one row from current ``AcqImage`` state.

        Args:
            file_id: Stable acquisition-file identifier.
            channel: Zero-based channel index.
            roi_id: ROI identifier.

        Raises:
            KeyError: If ``file_id`` is not present in the owning list.
        """
        acq_image = self._get_required_acq_image(file_id)
        row = self._build_row(acq_image, channel=int(channel), roi_id=int(roi_id))
        row_id = str(row["pool_row_id"])
        existing = self._df["pool_row_id"] == row_id if "pool_row_id" in self._df.columns else []
        if len(self._df) and bool(existing.any()):
            for column in self.columns:
                self._df.loc[existing, column] = row[column]
        else:
            self._df = pd.concat(
                [self._df, pd.DataFrame([row], columns=self.columns)],
                ignore_index=True,
            )
        self._sort_rows()
        self._reset_display_row_numbers()

    def remove_row(self, file_id: str, *, channel: int, roi_id: int) -> None:
        """Remove one row if present.

        Args:
            file_id: Stable acquisition-file identifier.
            channel: Zero-based channel index.
            roi_id: ROI identifier.
        """
        row_id = self.build_pool_row_id(file_id, channel=channel, roi_id=roi_id)
        if "pool_row_id" not in self._df.columns:
            return
        self._df = self._df.loc[self._df["pool_row_id"] != row_id].reset_index(drop=True)
        self._reset_display_row_numbers()

    def remove_roi(self, file_id: str, *, roi_id: int) -> None:
        """Remove all rows for one file/ROI across channels.

        Args:
            file_id: Stable acquisition-file identifier.
            roi_id: ROI identifier.
        """
        if self._df.empty:
            return
        mask = (self._df["path"] == str(file_id)) & (self._df["roi_id"] == int(roi_id))
        self._df = self._df.loc[~mask].reset_index(drop=True)
        self._reset_display_row_numbers()

    def to_csv(self, path: str | Path) -> None:
        """Write the current pool DataFrame to CSV.

        Args:
            path: Destination CSV path. Parent directories are created when
                needed.
        """
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._df.to_csv(out_path, index=False)

    @classmethod
    def build_pool_row_id(cls, file_id: str, *, channel: int, roi_id: int) -> str:
        """Return the canonical unique pool row identifier.

        Args:
            file_id: Stable acquisition-file identifier, currently the resolved
                source path.
            channel: Zero-based channel index.
            roi_id: ROI identifier.

        Returns:
            Stable string suitable for GUI unique-row-id contracts.
        """
        return f"{file_id}|channel={int(channel)}|roi_id={int(roi_id)}"

    def _get_required_acq_image(self, file_id: str) -> AcqImage:
        acq_image = self._acq_image_list.get_file_by_id(file_id)
        if acq_image is None:
            raise KeyError(f"file_id not found in AcqImageList: {file_id!r}")
        return acq_image

    def _iter_selection_keys(self, acq_image: AcqImage) -> list[tuple[int, int]]:
        keys: set[tuple[int, int]] = set()
        for channel in self._iter_channels(acq_image):
            for roi_id in self._iter_roi_ids(acq_image):
                keys.add((int(channel), int(roi_id)))

        analysis_set = getattr(acq_image, "analysis_set", None)
        if analysis_set is not None:
            for analysis in analysis_set.as_list():
                if self._is_pool_analysis(analysis):
                    keys.add((int(analysis.key.channel), int(analysis.key.roi_id)))
        return sorted(keys)

    def _iter_channels(self, acq_image: AcqImage) -> Sequence[int]:
        images = getattr(acq_image, "images", None)
        channels = getattr(images, "channels", None)
        if callable(channels):
            return tuple(int(channel) for channel in channels())
        num_channels = getattr(images, "num_channels", None)
        if num_channels is not None:
            return tuple(range(int(num_channels)))
        try:
            schema_row = acq_image.get_schema_row()
            return tuple(range(int(schema_row.get("num_channels", 0))))
        except Exception:
            return ()

    def _iter_roi_ids(self, acq_image: AcqImage) -> Sequence[int]:
        rois = getattr(acq_image, "rois", None)
        get_roi_ids = getattr(rois, "get_roi_ids", None)
        if callable(get_roi_ids):
            return tuple(int(roi_id) for roi_id in get_roi_ids())
        return ()

    def _is_pool_analysis(self, analysis: BaseAnalysis) -> bool:
        return any(
            analysis.key.analysis_name == analysis_cls.analysis_name
            for _, analysis_cls in self.analysis_specs
        )

    def _build_row(self, acq_image: AcqImage, *, channel: int, roi_id: int) -> dict[str, object]:
        base = self._build_base_row(acq_image, channel=channel, roi_id=roi_id)
        row: dict[str, object] = {column: base.get(column, pd.NA) for column in self.base_columns}
        analysis_set = getattr(acq_image, "analysis_set", None)
        for prefix, analysis_cls in self.analysis_specs:
            values: dict[str, object] = {}
            if analysis_set is not None:
                key = AnalysisKey(
                    analysis_name=analysis_cls.analysis_name,
                    channel=int(channel),
                    roi_id=int(roi_id),
                )
                analysis = analysis_set.get(key)
                if analysis is not None:
                    values = analysis.get_summary_values()
            for column in analysis_cls.get_summary_columns():
                row[f"{prefix}_{column}"] = values.get(column, pd.NA)
        return {column: row.get(column, pd.NA) for column in self.columns}

    def _build_base_row(self, acq_image: AcqImage, *, channel: int, roi_id: int) -> dict[str, object]:
        schema_row = acq_image.get_schema_row()
        step_y, step_x = self._safe_physical_units(acq_image)
        file_id = str(getattr(acq_image, "file_id", schema_row.get("path", "")))
        return {
            "pool_row_id": self.build_pool_row_id(file_id, channel=channel, roi_id=roi_id),
            "pool_row": 0,
            "name": schema_row.get("name", Path(file_id).name),
            "path": file_id,
            "parent": schema_row.get("parent", pd.NA),
            "grandparent": schema_row.get("grandparent", pd.NA),
            "condition": schema_row.get("condition", pd.NA),
            "genotype": schema_row.get("genotype", pd.NA),
            "accept": schema_row.get("accept", pd.NA),
            "channel": int(channel),
            "roi_id": int(roi_id),
            "step_y": step_y,
            "step_x": step_x,
        }

    def _safe_physical_units(self, acq_image: AcqImage) -> tuple[object, object]:
        getter = getattr(acq_image, "get_image_physical_units", None)
        if not callable(getter):
            return (pd.NA, pd.NA)
        try:
            step_y, step_x = getter()
        except Exception:
            return (pd.NA, pd.NA)
        return (step_y, step_x)

    def _sort_rows(self) -> None:
        if self._df.empty:
            return
        self._df = self._df.sort_values(
            by=["path", "channel", "roi_id"],
            kind="stable",
        ).reset_index(drop=True)

    def _reset_display_row_numbers(self) -> None:
        if "pool_row" in self._df.columns:
            self._df["pool_row"] = range(len(self._df))
