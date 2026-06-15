"""DataFrame processing helpers for NicePool plots."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE


class DataFrameProcessor:
    """Process DataFrames for NicePool filtering and plotting.

    Args:
        df: Source DataFrame.
        pre_filter_columns: Categorical pre-filter columns.
        unique_row_id_col: Stable row identifier column.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        pre_filter_columns: list[str],
        unique_row_id_col: str,
    ) -> None:
        self.df = df.copy()
        self.pre_filter_columns = [column for column in pre_filter_columns if column in df.columns]
        self.unique_row_id_col = unique_row_id_col
        if unique_row_id_col not in df.columns:
            raise ValueError(f"df must contain required unique id column {unique_row_id_col!r}")

    def get_pre_filter_values(self, column: str) -> list[str]:
        """Return sorted string values for one pre-filter column.

        Args:
            column: Pre-filter column.

        Returns:
            Sorted values as strings.
        """
        if column not in self.df.columns:
            return []
        values = self.df[column].dropna().map(str).unique().tolist()
        return sorted(values)

    def filter_by_pre_filters(self, selections: dict[str, Any]) -> pd.DataFrame:
        """Filter rows by active pre-filter selections.

        Args:
            selections: Mapping from pre-filter column to selected value.

        Returns:
            Filtered DataFrame.
        """
        filtered = self.df
        for column in self.pre_filter_columns:
            value = selections.get(column, PRE_FILTER_NONE)
            if value in (None, PRE_FILTER_NONE):
                continue
            filtered = filtered.loc[filtered[column].map(str) == str(value)]
        return filtered.dropna(subset=[self.unique_row_id_col])

    def get_x_values(
        self,
        df_f: pd.DataFrame,
        xcol: str,
        *,
        use_absolute: bool = False,
        use_remove_values: bool = False,
        remove_values_threshold: float | None = None,
    ) -> pd.Series:
        """Return x values with optional numeric transforms.

        Args:
            df_f: Filtered DataFrame.
            xcol: X column.
            use_absolute: Whether to apply absolute value to numeric values.
            use_remove_values: Whether to set large values to missing.
            remove_values_threshold: Symmetric threshold for removal.

        Returns:
            Series suitable for plotting.
        """
        return self._get_values(
            df_f,
            xcol,
            use_absolute=use_absolute,
            use_remove_values=use_remove_values,
            remove_values_threshold=remove_values_threshold,
        )

    def get_y_values(
        self,
        df_f: pd.DataFrame,
        ycol: str,
        *,
        use_absolute: bool = False,
        use_remove_values: bool = False,
        remove_values_threshold: float | None = None,
    ) -> pd.Series:
        """Return y values with optional numeric transforms.

        Args:
            df_f: Filtered DataFrame.
            ycol: Y column.
            use_absolute: Whether to apply absolute value to numeric values.
            use_remove_values: Whether to set large values to missing.
            remove_values_threshold: Symmetric threshold for removal.

        Returns:
            Numeric series suitable for plotting.
        """
        return pd.to_numeric(
            self._get_values(
                df_f,
                ycol,
                use_absolute=use_absolute,
                use_remove_values=use_remove_values,
                remove_values_threshold=remove_values_threshold,
            ),
            errors="coerce",
        )

    def _get_values(
        self,
        df_f: pd.DataFrame,
        column: str,
        *,
        use_absolute: bool,
        use_remove_values: bool,
        remove_values_threshold: float | None,
    ) -> pd.Series:
        if column not in df_f.columns:
            return pd.Series(dtype=float)
        source = df_f[column]
        if getattr(source.dtype, "kind", None) not in {"i", "u", "f"}:
            return source
        values = pd.to_numeric(source, errors="coerce")
        if use_absolute:
            values = values.abs()
        if use_remove_values and remove_values_threshold is not None:
            values = values.copy()
            values[(values < -remove_values_threshold) | (values > remove_values_threshold)] = np.nan
        return values
