"""Controller that keeps the AcqImageList velocity pool synchronized.

The velocity pool is owned by ``AcqImageList`` in acqstore. This controller is
CloudScope glue: it listens to model-change events from other controllers,
applies the corresponding pool mutation, and publishes ``VelocityPoolChanged``
for views. Keeping this logic here avoids scattering pool-specific refresh code
through ROI, analysis, and event-analysis controllers.
"""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.analysis.batch.types import BatchFileOutcome

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisChanged,
    AnalysisCompleted,
    AnalysisKind,
    BatchFileAnalysisCompleted,
)
from cloudscope.events.files import FileListChanged
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.events.velocity_pool import VelocityPoolChanged, VelocityPoolChangeKind
from cloudscope.state import PrimarySelection


@dataclass(slots=True)
class VelocityPoolController:
    """Synchronize ``AcqImageList.velocity_analysis_pool`` with app mutations.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: Controller owning the current ``AcqImageList`` state.
    """

    event_bus: EventBus
    home_controller: HomePageController

    def bind(self) -> None:
        """Subscribe to model-change events relevant to the velocity pool.

        Returns:
            None.
        """
        self.event_bus.subscribe(FileListChanged, self._on_file_list_changed)
        self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed)
        self.event_bus.subscribe(AnalysisChanged, self._on_analysis_changed)
        self.event_bus.subscribe(BatchFileAnalysisCompleted, self._on_batch_file_completed)
        self.event_bus.subscribe(RoiChanged, self._on_roi_changed)

    def _on_file_list_changed(self, event: FileListChanged) -> None:
        """Rebuild the pool after the loaded file list changes.

        Args:
            event: File-list state event.

        Returns:
            None.
        """
        _ = event
        pool = self._velocity_pool()
        if pool is None:
            return
        pool.rebuild()
        self.event_bus.publish(VelocityPoolChanged(change_kind=VelocityPoolChangeKind.REBUILD))

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh one pool row after a successful analysis run.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        if not event.success or not self._analysis_kind_affects_velocity_pool(event.analysis_kind):
            return
        self._refresh_selection_row(event.selection)

    def _on_analysis_changed(self, event: AnalysisChanged) -> None:
        """Refresh one pool row after direct analysis mutation.

        Args:
            event: Analysis-changed event.

        Returns:
            None.
        """
        if not self._analysis_kind_affects_velocity_pool(event.analysis_kind):
            return
        self._refresh_selection_row(event.selection)

    def _on_batch_file_completed(self, event: BatchFileAnalysisCompleted) -> None:
        """Refresh one pool row as a batch file completes.

        Args:
            event: Per-file batch completion event.

        Returns:
            None.
        """
        if not self._analysis_kind_affects_velocity_pool(event.analysis_kind):
            return
        result = event.result
        if result.outcome is not BatchFileOutcome.OK or result.roi_id is None:
            return
        self._refresh_row(
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
        pool = self._velocity_pool()
        if pool is None:
            return
        if event.operation is RoiChangeKind.DELETE:
            pool.remove_roi(file_id, roi_id=int(roi_id))
            self.event_bus.publish(
                VelocityPoolChanged(
                    change_kind=VelocityPoolChangeKind.REMOVE_ROI,
                    file_id=file_id,
                    roi_id=int(roi_id),
                )
            )
            return
        channel = event.selection.channel
        if channel is None:
            return
        self._refresh_row(file_id=file_id, channel=int(channel), roi_id=int(roi_id))

    def _refresh_selection_row(self, selection: PrimarySelection) -> None:
        """Refresh the pool row for a complete selection.

        Args:
            selection: Selection identifying the affected row.

        Returns:
            None.
        """
        if selection.file_id is None or selection.channel is None or selection.roi_id is None:
            return
        self._refresh_row(
            file_id=selection.file_id,
            channel=int(selection.channel),
            roi_id=int(selection.roi_id),
        )

    def _refresh_row(self, *, file_id: str, channel: int, roi_id: int) -> None:
        pool = self._velocity_pool()
        if pool is None:
            return
        pool.refresh_row(file_id, channel=int(channel), roi_id=int(roi_id))
        self.event_bus.publish(
            VelocityPoolChanged(
                change_kind=VelocityPoolChangeKind.REFRESH_ROW,
                file_id=file_id,
                channel=int(channel),
                roi_id=int(roi_id),
            )
        )

    def _velocity_pool(self):
        acq_image_list = self.home_controller.state.acq_image_list
        if acq_image_list is None:
            return None
        return getattr(acq_image_list, "velocity_analysis_pool", None)

    @staticmethod
    def _analysis_kind_affects_velocity_pool(analysis_kind: AnalysisKind) -> bool:
        return analysis_kind in (AnalysisKind.RADON_VELOCITY, AnalysisKind.EVENT)
