"""Analysis collection owned by one AcqImage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from acqstore.acq_image.analysis.data_provider import AnalysisDataProvider
from acqstore.acq_image.analysis.model import (
    AnalysisExclusionError,
    AnalysisKey,
    AnalysisResult,
    AnalysisRunContext,
    BaseAnalysis,
)
from acqstore.acq_image.analysis.registry import get_analysis_class


class AcqAnalysisSet:
    """Collection and orchestrator for analyses owned by one AcqImage.

    Args:
        source_path: Source acquisition file path.
        data_provider: Thin provider used by analyses to access ROI image data
            and physical units.
    """

    def __init__(
        self,
        source_path: str | Path,
        data_provider: AnalysisDataProvider | None = None,
    ) -> None:
        self.source_path = str(source_path)
        self._data_provider = data_provider
        self._analyses: dict[AnalysisKey, BaseAnalysis] = {}
        self._dirty = False

    def is_dirty(self) -> bool:
        """Return whether this set or any child analysis is dirty.

        Returns:
            True if unsaved changes exist.
        """
        return self._dirty or any(analysis.is_dirty() for analysis in self._analyses.values())

    def set_dirty(self) -> None:
        """Mark this analysis set dirty.

        Returns:
            None.
        """
        self._dirty = True

    def set_clean(self) -> None:
        """Mark this set and all child analyses clean.

        Returns:
            None.
        """
        self._dirty = False
        for analysis in self._analyses.values():
            analysis.set_clean()

    def add(self, analysis: BaseAnalysis) -> None:
        """Add one analysis instance.

        Args:
            analysis: Analysis instance to store.

        Raises:
            ValueError: If an analysis already exists with the same key.
            AnalysisExclusionError: If another analysis in the same
                ``exclusive_group`` already exists for the same
                ``(channel, roi_id)``.
        """
        if analysis.key in self._analyses:
            raise ValueError(f"Analysis already exists: {analysis.key}")
        self._raise_if_exclusive_conflict(analysis)
        self.require_dependencies(analysis)
        self._analyses[analysis.key] = analysis
        self.set_dirty()

    def _raise_if_exclusive_conflict(self, analysis: BaseAnalysis) -> None:
        """Raise if another analysis in the same exclusive group is present.

        Args:
            analysis: Candidate analysis being added.

        Raises:
            AnalysisExclusionError: If another analysis with the same non-None
                ``exclusive_group`` already exists for the same
                ``(channel, roi_id)``.
        """
        group = analysis.exclusive_group
        if group is None:
            return
        channel = analysis.key.channel
        roi_id = analysis.key.roi_id
        analysis_name = analysis.key.analysis_name
        for existing in self._analyses.values():
            if existing.exclusive_group != group:
                continue
            if existing.key.channel != channel or existing.key.roi_id != roi_id:
                continue
            if existing.key.analysis_name == analysis_name:
                continue
            raise AnalysisExclusionError(
                f"Cannot add {analysis_name!r}: {existing.key.analysis_name!r} already "
                f"exists for channel={channel}, roi_id={roi_id} "
                f"(exclusive group {group!r})"
            )

    def get_primary_kymograph_analysis(
        self,
        *,
        channel: int,
        roi_id: int,
    ) -> BaseAnalysis | None:
        """Return the active ``primary_kymograph`` analysis for one selection.

        Args:
            channel: Channel index.
            roi_id: ROI identifier.

        Returns:
            The single analysis with ``exclusive_group == "primary_kymograph"``
            for the given ``(channel, roi_id)``, or None.
        """
        return self.get_exclusive_group_analysis(
            group="primary_kymograph",
            channel=channel,
            roi_id=roi_id,
        )

    def get_exclusive_group_analysis(
        self,
        *,
        group: str,
        channel: int,
        roi_id: int,
    ) -> BaseAnalysis | None:
        """Return the single analysis in an exclusive group for one selection.

        Args:
            group: Exclusive group name.
            channel: Channel index.
            roi_id: ROI identifier.

        Returns:
            Matching analysis, or None when no analysis is present.
        """
        for analysis in self._analyses.values():
            if analysis.exclusive_group != group:
                continue
            if analysis.key.channel != channel or analysis.key.roi_id != roi_id:
                continue
            return analysis
        return None

    def create(
        self,
        analysis_name: str,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, Any] | None = None,
    ) -> BaseAnalysis:
        """Create and add one analysis instance.

        Args:
            analysis_name: Registered analysis type name.
            channel: Channel index.
            roi_id: ROI identifier.
            detection_params: Optional detection parameter values.

        Returns:
            Newly created analysis instance.

        Raises:
            KeyError: If the analysis type is not registered.
            ValueError: If duplicate analysis identity already exists.
        """
        cls = get_analysis_class(analysis_name)
        analysis = cls(channel=channel, roi_id=roi_id, detection_params=detection_params)
        self.add(analysis)
        return analysis

    def get_or_create(
        self,
        analysis_name: str,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, Any] | None = None,
    ) -> BaseAnalysis:
        """Return an existing analysis or create it when missing.

        Args:
            analysis_name: Registered analysis type name.
            channel: Channel index.
            roi_id: ROI identifier.
            detection_params: Optional detection parameter values used only when
                creating a new analysis.

        Returns:
            Existing or newly created analysis.
        """
        key = AnalysisKey(
            analysis_name=analysis_name,
            channel=channel,
            roi_id=roi_id,
        )
        existing = self.get(key)
        if existing is not None:
            return existing
        return self.create(
            analysis_name,
            channel=channel,
            roi_id=roi_id,
            detection_params=detection_params,
        )

    def get(self, key: AnalysisKey) -> BaseAnalysis | None:
        """Return analysis by key.

        Args:
            key: Analysis identity.

        Returns:
            Analysis instance, or None if missing.
        """
        return self._analyses.get(key)

    def get_required(self, key: AnalysisKey) -> BaseAnalysis:
        """Return analysis by key or raise.

        Args:
            key: Analysis identity.

        Returns:
            Analysis instance.

        Raises:
            KeyError: If no analysis exists for the key.
        """
        analysis = self.get(key)
        if analysis is None:
            raise KeyError(f"Analysis not found: {key}")
        return analysis

    def remove(self, key: AnalysisKey) -> bool:
        """Remove one analysis by key.

        Args:
            key: Analysis identity to remove.

        Returns:
            True if an analysis was removed, False if no analysis existed for
            the key.
        """
        if key not in self._analyses:
            return False
        del self._analyses[key]
        self.set_dirty()
        return True

    def as_list(self) -> list[BaseAnalysis]:
        """Return analyses in insertion order.

        Returns:
            List of analyses.
        """
        return list(self._analyses.values())

    def require_dependencies(self, analysis: BaseAnalysis) -> dict[str, BaseAnalysis]:
        """Return dependency analyses required by one analysis.

        Args:
            analysis: Analysis whose dependencies should be resolved.

        Returns:
            Mapping from dependency analysis name to dependency instance.

        Raises:
            ValueError: If a required dependency is missing.
        """
        dependencies: dict[str, BaseAnalysis] = {}
        for dependency_name in analysis.depends_on:
            key = AnalysisKey(
                analysis_name=dependency_name,
                channel=analysis.key.channel,
                roi_id=analysis.key.roi_id,
            )
            dependency = self.get(key)
            if dependency is None:
                raise ValueError(
                    f"{analysis.key.analysis_name!r} requires {dependency_name!r} "
                    f"for channel={analysis.key.channel}, roi_id={analysis.key.roi_id}"
                )
            dependencies[dependency_name] = dependency
        return dependencies

    def run_analysis(
        self,
        key: AnalysisKey,
        *,
        context: AnalysisRunContext | None = None,
    ) -> AnalysisResult:
        """Run one analysis by key.

        Args:
            key: Analysis identity.
            context: Optional progress/cancellation context.

        Returns:
            Analysis result.

        Raises:
            RuntimeError: If no data provider was configured.
            KeyError: If the analysis does not exist.
            ValueError: If required dependencies are missing.
        """
        if self._data_provider is None:
            raise RuntimeError("Cannot run analysis without a data provider")

        analysis = self.get_required(key)
        dependencies = self.require_dependencies(analysis)
        result = analysis.run(
            self._data_provider,
            context=context,
            dependencies=dependencies,
        )
        self.set_dirty()
        return result

    def delete_roi(self, roi_id: int) -> int:
        """Delete analyses depending on one ROI.

        Args:
            roi_id: ROI identifier that was deleted.

        Returns:
            Number of analyses removed.
        """
        keys = [key for key in self._analyses if key.roi_id == roi_id]
        for key in keys:
            del self._analyses[key]
        if keys:
            self.set_dirty()
        return len(keys)

    def edit_roi(self, roi_id: int) -> int:
        """Delete analyses depending on one edited ROI.

        For v1, ROI edits invalidate dependent analyses and users can rerun
        analysis after the edit.

        Args:
            roi_id: ROI identifier that was edited.

        Returns:
            Number of analyses removed.
        """
        return self.delete_roi(roi_id)

    def serialize_json_analysis(self) -> list[dict[str, Any]]:
        """Return JSON-serializable records for all analyses.

        Returns:
            List of analysis records to store under the AcqImage sidecar JSON
            ``"analysis"`` key.
        """
        return [analysis.to_json_dict() for analysis in self._analyses.values()]

    def load_json_analysis(self, records: list[dict[str, Any]]) -> None:
        """Replace analyses from JSON records.

        Args:
            records: Analysis records loaded from the AcqImage sidecar JSON
                ``"analysis"`` key.

        Returns:
            None.

        Raises:
            KeyError: If any analysis class is not registered.
            ValueError: If duplicate records exist.
        """
        self._analyses.clear()

        for record in records:
            analysis_name = str(record["analysis_name"])
            channel = int(record["channel"])
            roi_id = int(record["roi_id"])
            cls = get_analysis_class(analysis_name)
            analysis = cls(channel=channel, roi_id=roi_id)
            analysis.load_json_dict(record)
            self.add(analysis)

        self.set_clean()

    def load_all_results_dfs_from_csv(self, source_path: str | Path) -> None:
        """Load CSV tables for all analyses with matching sidecar files.

        Args:
            source_path: Source acquisition file path.

        Returns:
            None.
        """
        source = Path(source_path)
        tables_by_name: dict[str, pd.DataFrame] = {}

        for analysis in self._analyses.values():
            analysis_name = analysis.key.analysis_name
            csv_path = self.analysis_csv_path(source, analysis_name)
            if csv_path.exists() and analysis_name not in tables_by_name:
                tables_by_name[analysis_name] = pd.read_csv(csv_path)

        for analysis in self._analyses.values():
            table = tables_by_name.get(analysis.key.analysis_name)
            if table is None:
                continue

            if "channel" not in table.columns or "roi_id" not in table.columns:
                raise ValueError(
                    f"Analysis CSV for {analysis.key.analysis_name!r} is missing "
                    "required channel/roi_id columns"
                )

            mask = (
                (table["channel"] == analysis.key.channel)
                & (table["roi_id"] == analysis.key.roi_id)
            )
            sub = table.loc[mask].copy()
            if sub.empty:
                continue
            analysis.result.table = sub.drop(columns=["channel", "roi_id"])

        self.set_clean()

    def save_results_df(self, source_path: str | Path) -> None:
        """Save combined CSV tables by analysis type.

        Args:
            source_path: Source acquisition file path.

        Returns:
            None.

        Raises:
            ValueError: If one analysis type produces inconsistent table columns.
        """
        source = Path(source_path)
        tables_by_name: dict[str, list[pd.DataFrame]] = {}

        for analysis in self._analyses.values():
            table = analysis.table_with_bookkeeping()
            if table is None:
                continue
            tables_by_name.setdefault(analysis.key.analysis_name, []).append(table)

        existing_names = {
            path.name.removeprefix(source.name + ".").removesuffix(".csv")
            for path in source.parent.glob(f"{source.name}.*.csv")
        }

        for analysis_name, tables in tables_by_name.items():
            self._validate_same_columns(analysis_name, tables)
            combined = pd.concat(tables, ignore_index=True)
            combined.to_csv(self.analysis_csv_path(source, analysis_name), index=False)

        for analysis_name in existing_names - set(tables_by_name.keys()):
            self.analysis_csv_path(source, analysis_name).unlink(missing_ok=True)

    @staticmethod
    def analysis_csv_path(source_path: str | Path, analysis_name: str) -> Path:
        """Return sidecar CSV path for one source file and analysis type.

        Args:
            source_path: Source acquisition file path.
            analysis_name: Analysis type name.

        Returns:
            Path such as ``myfile.tif.velocity.csv``.
        """
        source = Path(source_path)
        return source.with_name(f"{source.name}.{analysis_name}.csv")

    @staticmethod
    def _validate_same_columns(
        analysis_name: str,
        tables: list[pd.DataFrame],
    ) -> None:
        """Validate same table columns for one analysis type.

        Args:
            analysis_name: Analysis type name.
            tables: Tables for that analysis type.

        Raises:
            ValueError: If table columns differ.
        """
        if not tables:
            return

        expected = list(tables[0].columns)
        for table in tables[1:]:
            actual = list(table.columns)
            if actual != expected:
                raise ValueError(
                    f"Analysis {analysis_name!r} produced inconsistent table columns: "
                    f"expected {expected}, got {actual}"
                )
