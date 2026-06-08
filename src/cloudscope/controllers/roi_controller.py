"""Controller for ROI creation, deletion, and edit-mode requests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from acqstore.acq_image.roi import RectROI, RectRoiBounds

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
    RoiEditPreviewChanged,
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
        self._pending_edit_selection: PrimarySelection | None = None
        self._pending_edit_bounds: RectRoiBounds | None = None

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
        self._event_bus.subscribe(RoiEditPreviewChanged, self._on_roi_edit_preview_changed)

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
        roi = acq_image.rois.get(event.selection.roi_id)
        if roi is None:
            self._publish_warning(f"ROI {event.selection.roi_id} no longer exists.")
            return
        if not isinstance(roi, RectROI):
            self._publish_warning(f"ROI {event.selection.roi_id} is not a rectangular ROI.")
            return

        self._pending_edit_selection = event.selection
        self._pending_edit_bounds = roi.bounds

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
                message=f"Editing ROI {event.selection.roi_id}.",
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
        self._clear_pending_edit()
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
        """Commit the staged ROI edit after optional analysis confirmation.

        Args:
            event: Submit-edit request.

        Returns:
            None.
        """
        acq_image = self._resolve_acq_image(event.selection)
        roi_id = event.selection.roi_id
        bounds = self._pending_edit_bounds
        if (
            acq_image is None
            or roi_id is None
            or bounds is None
            or self._pending_edit_selection != event.selection
        ):
            self._publish_warning("Cannot submit ROI edit without an active staged edit.")
            return
        roi = acq_image.rois.get(roi_id)
        if not isinstance(roi, RectROI):
            self._publish_warning(f"ROI {roi_id} is not a rectangular ROI.")
            return

        dependencies = self._analysis_dependencies_for_roi(acq_image, roi_id)
        if dependencies:
            title, message = self._build_edit_message(roi_id, dependencies)
            self._dialog_factory(
                title=title,
                message=message,
                yes_label="Edit ROI",
                no_label="No",
                cancel_label="Cancel",
                on_yes=lambda: self._commit_rect_roi_edit(acq_image, event.selection, bounds),
                on_no=lambda: self._cancel_submitted_edit(event.selection),
            ).open()
            return

        self._commit_rect_roi_edit(acq_image, event.selection, bounds)

    def _on_apply_full_width(self, event: ApplyRoiFullWidthIntent) -> None:
        """Stage a full-width edit for the active rectangular ROI.

        Args:
            event: Full-width edit request.

        Returns:
            None.
        """
        self._stage_full_extent_edit(event.selection, full_width=True)

    def _on_apply_full_height(self, event: ApplyRoiFullHeightIntent) -> None:
        """Stage a full-height edit for the active rectangular ROI.

        Args:
            event: Full-height edit request.

        Returns:
            None.
        """
        self._stage_full_extent_edit(event.selection, full_width=False)

    def _on_roi_edit_preview_changed(self, event: RoiEditPreviewChanged) -> None:
        """Cache latest staged ROI edit preview.

        Args:
            event: Preview bounds event from the image view.

        Returns:
            None.
        """
        if self._pending_edit_selection != event.selection:
            return
        self._pending_edit_bounds = event.bounds

    def _delete_roi(self, acq_image: AcqImage, selection: PrimarySelection) -> None:
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

    def _commit_rect_roi_edit(
        self,
        acq_image: AcqImage,
        selection: PrimarySelection,
        bounds: RectRoiBounds,
    ) -> None:
        """Apply staged rectangular ROI bounds and publish edit state.

        Args:
            acq_image: Acquisition image owning the ROI.
            selection: Selection snapshot identifying the ROI.
            bounds: New rectangular bounds.

        Returns:
            None.
        """
        roi_id = selection.roi_id
        if roi_id is None:
            raise ValueError("Cannot edit ROI without roi_id")

        removed_analysis_count = acq_image.analysis_set.delete_roi(roi_id)
        acq_image.rois.edit_rect_roi(roi_id, bounds=bounds)
        self._home_page_controller.select_roi(roi_id)
        new_selection = self._selection_with_roi(selection, roi_id)
        self._clear_pending_edit()
        self._event_bus.publish(
            RoiChanged(
                operation=RoiChangeKind.EDIT,
                selection=new_selection,
                removed_analysis_count=removed_analysis_count,
            )
        )
        self._event_bus.publish(
            RoiEditModeChanged(
                is_editing=False,
                selection=None,
                message=f"ROI {roi_id} edit submitted.",
            )
        )

    def _stage_full_extent_edit(self, selection: PrimarySelection, *, full_width: bool) -> None:
        """Stage a full-width or full-height preview for the active edit.

        Args:
            selection: Selection snapshot identifying the active ROI.
            full_width: True for dim1/full-width; False for dim0/full-height.

        Returns:
            None.
        """
        acq_image = self._resolve_acq_image(selection)
        roi_id = selection.roi_id
        if acq_image is None or roi_id is None:
            self._publish_warning("Cannot edit ROI without a selected file and ROI.")
            return
        if self._pending_edit_selection != selection or self._pending_edit_bounds is None:
            self._publish_warning("Cannot apply full extent without an active ROI edit.")
            return
        bounds = self._pending_edit_bounds
        image_bounds = acq_image.rois.image_bounds
        if full_width:
            new_bounds = RectRoiBounds(
                dim0_start=0,
                dim0_stop=image_bounds.height,
                dim1_start=bounds.dim1_start,
                dim1_stop=bounds.dim1_stop,
            )
        else:
            new_bounds = RectRoiBounds(
                dim0_start=bounds.dim0_start,
                dim0_stop=bounds.dim0_stop,
                dim1_start=0,
                dim1_stop=image_bounds.width,
            )
        new_bounds = new_bounds.clamped_to(image_bounds)
        self._pending_edit_bounds = new_bounds
        self._event_bus.publish(
            RoiEditPreviewChanged(selection=selection, bounds=new_bounds)
        )

    def _clear_pending_edit(self) -> None:
        """Clear staged edit state.

        Returns:
            None.
        """
        self._pending_edit_selection = None
        self._pending_edit_bounds = None

    def _cancel_submitted_edit(self, selection: PrimarySelection) -> None:
        """Cancel a submitted edit when the confirmation dialog is declined.

        Args:
            selection: Selection snapshot for the submitted edit.

        Returns:
            None.
        """
        if self._pending_edit_selection != selection:
            return
        self._clear_pending_edit()
        self._event_bus.publish(
            RoiEditModeChanged(
                is_editing=False,
                selection=None,
                message="ROI edit cancelled.",
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
        acq_image: AcqImage,
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
    def _dependency_from_analysis(analysis: BaseAnalysis) -> RoiAnalysisDependency:
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
    def _build_edit_message(
        roi_id: int,
        dependencies: list[RoiAnalysisDependency],
    ) -> tuple[str, str]:
        """Build confirmation text for ROI edits that invalidate analyses.

        Args:
            roi_id: ROI being edited.
            dependencies: Dependent analyses that will be removed.

        Returns:
            Title and body text for the confirmation dialog.
        """
        lines = [
            f"Editing ROI {roi_id} will remove dependent analysis:",
            "",
        ]
        for dependency in dependencies:
            lines.append(f"• {dependency.analysis_name}, channel {dependency.channel}")
        lines.extend(
            [
                "",
                "Changes are not written to disk until you save the file.",
            ]
        )
        return f"Edit ROI {roi_id}?", "\n".join(lines)

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
