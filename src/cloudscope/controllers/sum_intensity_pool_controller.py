"""Controller that keeps the AcqImageList sum-intensity pool synchronized.

The sum-intensity pool is owned by ``AcqImageList`` in acqstore. This controller
is CloudScope glue: it listens to model-change events from other controllers,
applies the corresponding pool mutation, and publishes
``SumIntensityPoolChanged`` for views.
"""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.analysis.batch.types import BatchFileOutcome
from acqstore.acq_image.metadata import ExperimentMetadata

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisChanged,
    AnalysisCompleted,
    AnalysisKind,
    BatchFileAnalysisCompleted,
)
from cloudscope.events.files import FileListChanged
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.events.sum_intensity_pool import (
    SumIntensityPoolChanged,
    SumIntensityPoolChangeKind,
)
from cloudscope.state import PrimarySelection


@dataclass(slots=True)
class SumIntensityPoolController:
    """Synchronize ``AcqImageList.sum_intensity_analysis_pool`` with mutations.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: Controller owning the current ``AcqImageList`` state.
    """

    event_bus: EventBus
    home_controller: HomePageController

    def bind(self) -> None:
        """Subscribe to model-change events relevant to the sum-intensity pool.

        Returns:
            None.
        """
        self.event_bus.subscribe(FileListChanged, self._on_file_list_changed)
        self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed)
        self.event_bus.subscribe(AnalysisChanged, self._on_analysis_changed)
        self.event_bus.subscribe(BatchFileAnalysisCompleted, self._on_batch_file_completed)
        self.event_bus.subscribe(RoiChanged, self._on_roi_changed)
        self.event_bus.subscribe(MetadataChanged, self._on_metadata_changed)

    def _on_file_list_changed(self, event: FileListChanged) -> None:
        """Rebuild the pool after the loaded file list changes.

        Args:
            event: File-list state event.

        Returns:
            None.
        """
        _ = event
        pool = self._sum_intensity_pool()
        if pool is None:
            return
        pool.rebuild()
        self.event_bus.publish(
            SumIntensityPoolChanged(change_kind=SumIntensityPoolChangeKind.REBUILD)
        )

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh rows after a successful sum-intensity analysis run.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        if not event.success or event.analysis_kind is not AnalysisKind.SUM_INTENSITY:
            return
        self._refresh_selection_rows(event.selection)

    def _on_analysis_changed(self, event: AnalysisChanged) -> None:
        """Refresh rows after direct sum-intensity analysis mutation.

        Args:
            event: Analysis-changed event.

        Returns:
            None.
        """
        if event.analysis_kind is not AnalysisKind.SUM_INTENSITY:
            return
        self._refresh_selection_rows(event.selection)

    def _on_batch_file_completed(self, event: BatchFileAnalysisCompleted) -> None:
        """Refresh rows as a sum-intensity batch file completes.

        Args:
            event: Per-file batch completion event.

        Returns:
            None.
        """
        if event.analysis_kind is not AnalysisKind.SUM_INTENSITY:
            return
        result = event.result
        if result.outcome is not BatchFileOutcome.OK or result.roi_id is None:
            return
        self._refresh_rows(
            file_id=event.file_id,
            channel=int(result.channel),
            roi_id=int(result.roi_id),
        )

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Apply pool mutation corresponding to a ROI change.

        Args:
            event: ROI model-change event.

        Returns:
            None.
        """
        file_id = event.selection.file_id
        roi_id = event.affected_roi_id
        if file_id is None or roi_id is None:
            return
        pool = self._sum_intensity_pool()
        if pool is None:
            return
        if event.operation is RoiChangeKind.DELETE:
            pool.remove_roi(file_id, roi_id=int(roi_id))
            self.event_bus.publish(
                SumIntensityPoolChanged(
                    change_kind=SumIntensityPoolChangeKind.REMOVE_ROI,
                    file_id=file_id,
                    roi_id=int(roi_id),
                )
            )
            return
        channel = event.selection.channel
        if channel is None:
            return
        self._refresh_rows(file_id=file_id, channel=int(channel), roi_id=int(roi_id))

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh pool rows after experiment metadata edits.

        Args:
            event: Metadata changed event for one file section.

        Returns:
            None.
        """
        if event.metadata_section_id != ExperimentMetadata.metadata_section_id:
            return
        pool = self._sum_intensity_pool()
        if pool is None:
            return
        pool.refresh_file(event.file_id)
        self.event_bus.publish(
            SumIntensityPoolChanged(
                change_kind=SumIntensityPoolChangeKind.REFRESH_FILE,
                file_id=event.file_id,
            )
        )

    def _refresh_selection_rows(self, selection: PrimarySelection) -> None:
        """Refresh the pool rows for a complete selection.

        Args:
            selection: Selection identifying the affected rows.

        Returns:
            None.
        """
        if selection.file_id is None or selection.channel is None or selection.roi_id is None:
            return
        self._refresh_rows(
            file_id=selection.file_id,
            channel=int(selection.channel),
            roi_id=int(selection.roi_id),
        )

    def _refresh_rows(self, *, file_id: str, channel: int, roi_id: int) -> None:
        pool = self._sum_intensity_pool()
        if pool is None:
            return
        pool.refresh_rows(file_id, channel=int(channel), roi_id=int(roi_id))
        self.event_bus.publish(
            SumIntensityPoolChanged(
                change_kind=SumIntensityPoolChangeKind.REFRESH_ROWS,
                file_id=file_id,
                channel=int(channel),
                roi_id=int(roi_id),
            )
        )

    def _sum_intensity_pool(self):
        acq_image_list = self.home_controller.state.acq_image_list
        if acq_image_list is None:
            return None
        return getattr(acq_image_list, "sum_intensity_analysis_pool", None)
