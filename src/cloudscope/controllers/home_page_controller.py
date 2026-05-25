"""Controller logic for the CloudScope home page."""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.acq_image_list import AcqImageList

from cloudscope.event_bus import EventBus
from cloudscope.events.files import FileListChanged
from cloudscope.events.metadata import ApplyMetadataIntent, MetadataChanged
from cloudscope.events.selection import (
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
    SelectChannelIntent,
    SelectFileIntent,
    SelectRoiIntent,
)
from cloudscope.state import PrimarySelection


@dataclass(slots=True)
class HomePageState:
    """Application state for the CloudScope home page.

    Args:
        file_ids: Stable file identifiers in display order.
        selection: Current primary selection state.
        acq_image_list: Current backend file list, if loaded.
    """

    file_ids: list[str]
    selection: PrimarySelection
    acq_image_list: AcqImageList | None = None


class HomePageController:
    """Coordinate intent events and publish resulting state events.

    This controller owns mutation of page-level state. Views publish intent
    events and subscribe to state events instead of directly mutating shared
    state or calling each other.
    """

    def __init__(self, event_bus: EventBus, initial_state: HomePageState | None = None) -> None:
        """Initialize the controller.

        Args:
            event_bus: Event bus used for subscribing to intent events and
                publishing resulting state events.
            initial_state: Optional initial state. If omitted, an empty state is
                created.
        """
        self._event_bus = event_bus
        self._state = initial_state or HomePageState(
            file_ids=[],
            selection=PrimarySelection(),
            acq_image_list=None,
        )

    @property
    def state(self) -> HomePageState:
        """Return the current controller state.

        Returns:
            Current home-page state object.
        """
        return self._state

    def bind(self) -> None:
        """Subscribe controller handlers to intent events.

        Returns:
            None.
        """
        self._event_bus.subscribe(SelectFileIntent, self._on_select_file)
        self._event_bus.subscribe(SelectChannelIntent, self._on_select_channel)
        self._event_bus.subscribe(SelectRoiIntent, self._on_select_roi)
        self._event_bus.subscribe(ApplyMetadataIntent, self._on_apply_metadata)

    def load_acq_image_list(self, acq_image_list: AcqImageList) -> None:
        """Replace the current file list with a backend AcqImageList.

        Args:
            acq_image_list: Backend acquisition-image list to use as the source
                of truth for files and default selection.

        Returns:
            None.
        """
        self._state.acq_image_list = acq_image_list
        self._state.file_ids = [acq_file.file_id for acq_file in acq_image_list.get_files()]
        self._event_bus.publish(
            FileListChanged(
                file_ids=list(self._state.file_ids),
                rows=acq_image_list.get_schema_rows(),
            )
        )

        file_id, channel, roi_id = acq_image_list.get_default_selection()
        self._state.selection = PrimarySelection(
            file_id=file_id,
            channel=channel,
            roi_id=roi_id,
        )
        self._publish_file_selection_changed()

    def load_demo_files(self, file_ids: list[str]) -> None:
        """Replace the current file list with demo data.

        Args:
            file_ids: File identifiers in display order.

        Returns:
            None.
        """
        self._state.acq_image_list = None
        self._state.file_ids = list(file_ids)
        self._event_bus.publish(FileListChanged(file_ids=list(self._state.file_ids), rows=[]))

        default_file_id = self._state.file_ids[0] if self._state.file_ids else None
        self._state.selection = PrimarySelection(
            file_id=default_file_id,
            channel=0 if default_file_id is not None else None,
            roi_id=None,
        )
        self._publish_file_selection_changed()

    def _on_select_file(self, event: SelectFileIntent) -> None:
        """Handle file selection changes.

        Args:
            event: Requested file selection intent.

        Returns:
            None.

        Raises:
            ValueError: If the requested file identifier is unknown.
        """
        if event.file_id is None:
            self._state.selection = PrimarySelection()
            self._publish_file_selection_changed()
            return

        if self._state.acq_image_list is not None:
            acq_file = self._state.acq_image_list.get_file_by_id(event.file_id)
            if acq_file is None:
                raise ValueError(f'Unknown file_id: {event.file_id!r}')

            self._state.selection = PrimarySelection(
                file_id=acq_file.file_id,
                channel=acq_file.get_default_channel(),
                roi_id=acq_file.get_default_roi(),
            )
            self._publish_file_selection_changed()
            return

        if event.file_id not in self._state.file_ids:
            raise ValueError(f'Unknown file_id: {event.file_id!r}')

        self._state.selection.file_id = event.file_id
        self._state.selection.channel = 0
        self._state.selection.roi_id = None
        self._publish_file_selection_changed()

    def _on_select_channel(self, event: SelectChannelIntent) -> None:
        """Handle channel selection changes.

        Args:
            event: Requested channel selection intent.

        Returns:
            None.
        """
        if self._state.selection.file_id is None and event.channel is not None:
            raise ValueError('Cannot select a channel without a selected file')

        self._state.selection.channel = event.channel
        self._event_bus.publish(ChannelSelectionChanged(channel=self._state.selection.channel))

    def select_roi(self, roi_id: int | None) -> None:
        """Set the selected ROI and publish ROI selection state.

        Args:
            roi_id: ROI identifier to select, or None to clear selection.

        Returns:
            None.

        Raises:
            ValueError: If selecting a ROI while no file is selected.
        """
        if self._state.selection.file_id is None and roi_id is not None:
            raise ValueError('Cannot select an ROI without a selected file')

        self._state.selection.roi_id = roi_id
        self._event_bus.publish(RoiSelectionChanged(roi_id=self._state.selection.roi_id))

    def _on_select_roi(self, event: SelectRoiIntent) -> None:
        """Handle ROI selection changes.

        Args:
            event: Requested ROI selection intent.

        Returns:
            None.
        """
        self.select_roi(event.roi_id)

    def _on_apply_metadata(self, event: ApplyMetadataIntent) -> None:
        """Apply in-memory metadata patch for one file section.

        Args:
            event: Apply request with file id, metadata section id, and field patch.

        Raises:
            RuntimeError: If no ``AcqImageList`` is loaded.
            ValueError: If the file or metadata section is unknown.
        """
        if self._state.acq_image_list is None:
            raise RuntimeError('Cannot apply metadata without a loaded AcqImageList')

        acq_image = self._state.acq_image_list.get_file_by_id(event.file_id)
        if acq_image is None:
            raise ValueError(f'Unknown file_id: {event.file_id!r}')

        acq_image.apply_metadata_patch(event.metadata_section_id, dict(event.patch))
        self._event_bus.publish(
            MetadataChanged(
                file_id=event.file_id,
                metadata_section_id=event.metadata_section_id,
                file_list_row=dict(acq_image.get_schema_row()),
            )
        )

    def _publish_file_selection_changed(self) -> None:
        """Publish file selection (includes default channel and ROI for that file).

        Returns:
            None.
        """
        acq_image = None
        fid = self._state.selection.file_id
        if fid is not None and self._state.acq_image_list is not None:
            acq_image = self._state.acq_image_list.get_file_by_id(fid)
        self._event_bus.publish(
            FileSelectionChanged(
                file_id=fid,
                acq_image=acq_image,
                channel=self._state.selection.channel,
                roi_id=self._state.selection.roi_id,
            )
        )
