"""Controller for ROI creation, deletion, and edit-mode requests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage
    from acqstore.acq_image.analysis.model import BaseAnalysis

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.roi import (
    AddRoiIntent,
    ApplyRoiFullHeightIntent,
    ApplyRoiFullWidthIntent,
    BeginEditRoiIntent,
    CancelEditRoiIntent,
    DeleteRoiIntent,
    RoiChanged,
    RoiChangeKind,
    RoiEditModeChanged,
    SubmitEditRoiIntent,
)
from cloudscope.events.status import AppStatusChanged, StatusLevel, StatusSource
from cloudscope.state import PrimarySelection



def _default_yes_no_dialog_factory(**kwargs):
    """Create the default NiceGUI yes/no confirmation dialog.

    Args:
        **kwargs: Keyword arguments forwarded to ``YesNoDialog``.

    Returns:
        Configured yes/no dialog instance.
    """
    from cloudscope.views.dialogs.yes_no_dialog import YesNoDialog

    return YesNoDialog(**kwargs)


@dataclass(frozen=True)
class RoiAnalysisDependency:
    """Description of one analysis depending on a ROI.

    Args:
        analysis_name: Registered analysis type name.
        channel: Channel index for the analysis.
        roi_id: ROI identifier for the analysis.
    """

    analysis_name: str
    channel: int
    roi_id: int


class RoiController:
    """Handle ROI CRUD intent events and publish ROI state changes.

    Args:
        event_bus: Page-scoped event bus.
        home_page_controller: Controller owning page state and selection events.
        dialog_factory: Factory used to create confirmation dialogs. Tests may
            inject a fake factory to avoid NiceGUI UI construction.
    """

    def __init__(
        self,
        event_bus: EventBus,
        home_page_controller: HomePageController,
        *,
        dialog_factory: Callable[..., object] = _default_yes_no_dialog_factory,
    ) -> None:
        self._event_bus = event_bus
        self._home_page_controller = home_page_controller
        self._dialog_factory = dialog_factory

    def bind(self) -> None:
        """Subscribe to ROI intent events.

        Returns:
            None.
        """
        self._event_bus.subscribe(AddRoiIntent, self._on_add_roi)
        self._event_bus.subscribe(DeleteRoiIntent, self._on_delete_roi)
        self._event_bus.subscribe(BeginEditRoiIntent, self._on_begin_edit_roi)
        self._event_bus.subscribe(CancelEditRoiIntent, self._on_cancel_edit_roi)
        self._event_bus.subscribe(SubmitEditRoiIntent, self._on_submit_edit_roi)
        self._event_bus.subscribe(ApplyRoiFullWidthIntent, self._on_apply_full_width)
        self._event_bus.subscribe(ApplyRoiFullHeightIntent, self._on_apply_full_height)

    def _on_add_roi(self, event: AddRoiIntent) -> None:
        """Create a full-image rectangular ROI for the selected file.

        Args:
            event: Add ROI request.

        Returns:
            None.
        """
        acq_image = self._resolve_acq_image(event.selection)
        if acq_image is None:
            self._publish_warning("Cannot add ROI without a selected file.")
            return

        roi = acq_image.rois.create_rect_roi()
        new_selection = self._selection_with_roi(event.selection, roi.roi_id)
        self._home_page_controller.select_roi(roi.roi_id)
        self._event_bus.publish(
            RoiChanged(
                operation=RoiChangeKind.ADD,
                selection=new_selection,
                removed_analysis_count=0,
            )
        )

    def _on_delete_roi(self, event: DeleteRoiIntent) -> None:
        """Delete a ROI after optional confirmation.

        Args:
            event: Delete ROI request.

        Returns:
            None.
        """
        acq_image = self._resolve_acq_image(event.selection)
        roi_id = event.selection.roi_id
        if acq_image is None or roi_id is None:
            self._publish_warning("Cannot delete ROI without a selected file and ROI.")
            return
        if not acq_image.rois.has_roi(roi_id):
            self._publish_warning(f"ROI {roi_id} no longer exists.")
            return

        dependencies = self._analysis_dependencies_for_roi(acq_image, roi_id)
        if dependencies:
            title, message = self._build_delete_message(roi_id, dependencies)
            self._dialog_factory(
                title=title,
                message=message,
                yes_label="Delete ROI",
                no_label="No",
                cancel_label="Cancel",
                on_yes=lambda: self._delete_roi(acq_image, event.selection),
                on_no=None,
            ).open()
            return

        self._delete_roi(acq_image, event.selection)

    def _on_begin_edit_roi(self, event: BeginEditRoiIntent) -> None:
        """Handle request to enter ROI edit mode.

        This milestone publishes explicit edit-mode state but intentionally
        defers geometry mutation to a later pass.

        Args:
            event: Begin-edit request.

        Returns:
            None.
        """
        if event.selection.file_id is None or event.selection.roi_id is None:
            self._publish_warning("Cannot edit ROI without a selected file and ROI.")
            return
        acq_image = self._resolve_acq_image(event.selection)
        if acq_image is None:
            self._publish_warning("Cannot edit ROI because the selected file is not loaded.")
            return
        if not acq_image.rois.has_roi(event.selection.roi_id):
            self._publish_warning(f"ROI {event.selection.roi_id} no longer exists.")
            return

        self._event_bus.publish(
            RoiEditModeChanged(
                is_editing=True,
                selection=event.selection,
                message=f"Editing ROI {event.selection.roi_id}.",
            )
        )
        self._event_bus.publish(
            AppStatusChanged(
                level=StatusLevel.INFO,
                message=f"Editing ROI {event.selection.roi_id}. Geometry editing is not implemented yet.",
                source=StatusSource.SYSTEM,
            )
        )

    def _on_cancel_edit_roi(self, event: CancelEditRoiIntent) -> None:
        """Handle cancellation of ROI edit mode.

        Args:
            event: Cancel-edit request.

        Returns:
            None.
        """
        self._event_bus.publish(
            RoiEditModeChanged(
                is_editing=False,
                selection=None,
                message="ROI edit cancelled.",
            )
        )
        self._event_bus.publish(
            AppStatusChanged(
                level=StatusLevel.INFO,
                message="ROI edit cancelled.",
                source=StatusSource.SYSTEM,
            )
        )

    def _on_submit_edit_roi(self, event: SubmitEditRoiIntent) -> None:
        """Handle ROI edit submission placeholder.

        Args:
            event: Submit-edit request.

        Returns:
            None.
        """
        self._event_bus.publish(
            RoiEditModeChanged(
                is_editing=False,
                selection=None,
                message="ROI edit submitted; geometry editing is not implemented yet.",
            )
        )
        self._publish_warning("ROI geometry editing is not implemented yet.")

    def _on_apply_full_width(self, event: ApplyRoiFullWidthIntent) -> None:
        """Handle full-width ROI edit placeholder.

        Args:
            event: Full-width edit request.

        Returns:
            None.
        """
        self._publish_warning("Full-width ROI edit is not implemented yet.")

    def _on_apply_full_height(self, event: ApplyRoiFullHeightIntent) -> None:
        """Handle full-height ROI edit placeholder.

        Args:
            event: Full-height edit request.

        Returns:
            None.
        """
        self._publish_warning("Full-height ROI edit is not implemented yet.")

    def _delete_roi(self, acq_image: "AcqImage", selection: PrimarySelection) -> None:
        """Delete one ROI and dependent analyses.

        Args:
            acq_image: Acquisition image owning the ROI.
            selection: Selection snapshot identifying the ROI to delete.

        Returns:
            None.
        """
        roi_id = selection.roi_id
        if roi_id is None:
            raise ValueError("Cannot delete ROI without roi_id")

        old_roi_ids = acq_image.rois.get_roi_ids()
        removed_analysis_count = acq_image.analysis_set.delete_roi(roi_id)
        acq_image.rois.delete(roi_id)
        next_roi_id = self._next_roi_id_after_delete(old_roi_ids, roi_id)
        new_selection = self._selection_with_roi(selection, next_roi_id)
        self._home_page_controller.select_roi(next_roi_id)
        self._event_bus.publish(
            RoiChanged(
                operation=RoiChangeKind.DELETE,
                selection=new_selection,
                removed_analysis_count=removed_analysis_count,
            )
        )

    def _resolve_acq_image(self, selection: PrimarySelection) -> AcqImage | None:
        """Resolve the selected AcqImage from page state.

        Args:
            selection: Selection snapshot containing ``file_id``.

        Returns:
            Matching AcqImage, or None when unavailable.
        """
        if selection.file_id is None:
            return None
        acq_image_list = self._home_page_controller.state.acq_image_list
        if acq_image_list is None:
            return None
        return acq_image_list.get_file_by_id(selection.file_id)

    def _analysis_dependencies_for_roi(
        self,
        acq_image: "AcqImage",
        roi_id: int,
    ) -> list[RoiAnalysisDependency]:
        """Return runtime analyses that depend on one ROI.

        Args:
            acq_image: Acquisition image containing an analysis set.
            roi_id: ROI identifier to inspect.

        Returns:
            List of analysis dependency descriptors.
        """
        dependencies: list[RoiAnalysisDependency] = []
        for analysis in acq_image.analysis_set.as_list():
            dependencies.append(self._dependency_from_analysis(analysis))
        return [dependency for dependency in dependencies if dependency.roi_id == roi_id]

    @staticmethod
    def _dependency_from_analysis(analysis: "BaseAnalysis") -> RoiAnalysisDependency:
        """Build one dependency descriptor from an analysis object.

        Args:
            analysis: Analysis instance.

        Returns:
            Dependency descriptor.
        """
        return RoiAnalysisDependency(
            analysis_name=analysis.key.analysis_name,
            channel=analysis.key.channel,
            roi_id=analysis.key.roi_id,
        )

    @staticmethod
    def _build_delete_message(
        roi_id: int,
        dependencies: list[RoiAnalysisDependency],
    ) -> tuple[str, str]:
        """Build confirmation text for a destructive ROI delete.

        Args:
            roi_id: ROI being deleted.
            dependencies: Dependent analyses that will be removed.

        Returns:
            Title and body text for the confirmation dialog.
        """
        lines = [
            f"ROI {roi_id} has analysis that will be removed:",
            "",
        ]
        for dependency in dependencies:
            lines.append(f"• {dependency.analysis_name}, channel {dependency.channel}")
        lines.extend(
            [
                "",
                "Deleting the ROI removes these in-memory analysis results. ",
                "Changes are not written to disk until you save the file.",
            ]
        )
        return f"Delete ROI {roi_id}?", "\n".join(lines)

    @staticmethod
    def _next_roi_id_after_delete(old_roi_ids: list[int], deleted_roi_id: int) -> int | None:
        """Choose the ROI that should be selected after deletion.

        Args:
            old_roi_ids: ROI ids before deletion, in display order.
            deleted_roi_id: ROI id that was deleted.

        Returns:
            Previous ROI id when possible, otherwise next ROI id, otherwise None.
        """
        remaining = [roi_id for roi_id in old_roi_ids if roi_id != deleted_roi_id]
        if not remaining:
            return None
        try:
            deleted_index = old_roi_ids.index(deleted_roi_id)
        except ValueError:
            return remaining[0]
        if deleted_index > 0:
            return old_roi_ids[deleted_index - 1]
        return remaining[0]

    @staticmethod
    def _selection_with_roi(selection: PrimarySelection, roi_id: int | None) -> PrimarySelection:
        """Return a copied selection with updated ROI id.

        Args:
            selection: Source selection.
            roi_id: Replacement ROI id.

        Returns:
            Copied selection with updated ROI id.
        """
        return PrimarySelection(
            file_id=selection.file_id,
            channel=selection.channel,
            roi_id=roi_id,
        )

    def _publish_warning(self, message: str) -> None:
        """Publish a warning status message.

        Args:
            message: User-visible warning.

        Returns:
            None.
        """
        self._event_bus.publish(
            AppStatusChanged(
                level=StatusLevel.WARNING,
                message=message,
                source=StatusSource.SYSTEM,
            )
        )
