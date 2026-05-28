"""
Application state definitions.
"""

from dataclasses import dataclass


@dataclass
class PrimarySelection:
    """Primary selection state.

    Attributes:
        file_id: Selected file identifier, or ``None`` when no file is
            selected.
        channel: Selected channel index, or ``None`` when no channel is
            selected.
        roi_id: Selected ROI identifier, or ``None`` when no ROI is
            selected.
        analysis_name: Optional analysis identity component used only when
            the user picked a specific analysis row in a tree view.

            Set to a non-``None`` value ONLY when the user selects an
            analysis child row in
            :class:`cloudscope.views.file_list_tree_view.AcqImageListTreeView`.
            Together with ``file_id``, ``channel``, and ``roi_id`` this
            uniquely identifies one analysis inside the file's
            :class:`acqstore.acq_image.acq_analysis_set.AcqAnalysisSet`,
            because :class:`acqstore.acq_image.analysis.model.AnalysisKey`
            identity is ``(analysis_name, channel, roi_id)`` and multiple
            analyses can share ``(channel, roi_id)`` (for example, a
            ``radon_velocity`` and a dependent ``event`` analysis).

            Consumers as of ticket 025:
              * ``AcqImageListTreeView._sync_table_selection`` reads this
                field to decide whether to highlight the parent file row
                or a specific analysis child row in the tree.

            Default ``None`` is used for:
              * File-row clicks (only ``file_id`` is meaningful).
              * Selections from non-tree views (legacy table view, batch
                dialogs, controller-initiated default selections).
              * Initial app state and cleared selections.
              * Channel-only and ROI-only selection changes, which clear
                this field because the previously-selected analysis row
                identity is no longer valid.

            Other current views that consume ``PrimarySelection``
            (primary image view, diameter view, velocity view, event
            view, table view) read only ``file_id`` / ``channel`` /
            ``roi_id`` and treat ``analysis_name`` as absent.
    """

    file_id: str | None = None
    channel: int | None = None
    roi_id: int | None = None
    analysis_name: str | None = None
