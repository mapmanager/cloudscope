"""Controller logic for the CloudScope home page."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.acq_image_list import AcqImageList

from cloudscope.event_bus import EventBus
from cloudscope.events.files import FileListChanged, ImageDataUnloaded, UnloadImageDataIntent
from cloudscope.events.metadata import ApplyMetadataIntent, MetadataChanged
from cloudscope.events.selection import (
    SELECTION_SOURCE_EXTERNAL,
    SELECTION_SOURCE_LOAD,
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
    SelectChannelIntent,
    SelectFileIntent,
    SelectRoiIntent,
)
from cloudscope.events.session_reconnect import HomePageSessionReconnectRestore
from cloudscope.session_state import HomePageSessionSnapshot
from cloudscope.state import PrimarySelection

if TYPE_CHECKING:
    from cloudscope.controllers.acq_image_data_controller import AcqImageDataController


@dataclass(slots=True)
class HomePageState:
    """Application state for the CloudScope home page.

    Args:
        file_ids: Stable file identifiers in display order.
        selection: Current primary selection state.
        acq_image_list: Current backend file list, if loaded.
        visible_file_ids_provider: Async callback returning file ids from the
            currently visible, filtered, sorted file-table rows. Set by the
            page composer once the file-table view exists; ``None`` while the
            file table is not yet reachable.
        primary_x_range: Current ``(x_min, x_max)`` pair for the synced x-axis
            shared by the primary raster and the 1D analysis plot. ``(None,
            None)`` means "auto" (use each widget's full extent). Mutated by
            :class:`XRangeController`; reset on ``FileSelectionChanged`` to
            different files, preserved across ``ChannelSelectionChanged``.
    """

    file_ids: list[str]
    selection: PrimarySelection
    acq_image_list: AcqImageList | None = None
    visible_file_ids_provider: Callable[[], Awaitable[list[str]]] | None = field(default=None)
    primary_x_range: tuple[float | None, float | None] = (None, None)


class HomePageController:
    """Coordinate intent events and publish resulting state events.

    This controller owns mutation of page-level state. Views publish intent
    events and subscribe to state events instead of directly mutating shared
    state or calling each other.
    """

    def __init__(
        self,
        event_bus: EventBus,
        *,
        acq_image_data_controller: AcqImageDataController | None = None,
        initial_state: HomePageState | None = None,
    ) -> None:
        """Initialize the controller.

        Args:
            event_bus: Event bus used for subscribing to intent events and
                publishing resulting state events.
            acq_image_data_controller: Optional controller that loads lazy
                acquisition data before :class:`FileSelectionChanged` is
                published. When omitted, file selection is published
                immediately (tests only).
            initial_state: Optional initial state. If omitted, an empty state is
                created.
        """
        self._event_bus = event_bus
        self._acq_image_data_controller = acq_image_data_controller
        self._state = initial_state or HomePageState(
            file_ids=[],
            selection=PrimarySelection(),
            acq_image_list=None,
        )
        self._pending_reconnect_snapshot: HomePageSessionSnapshot | None = None

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
        self._event_bus.subscribe(UnloadImageDataIntent, self._on_unload_image_data)

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
        self._publish_file_selection_after_lazy_data_loaded(SELECTION_SOURCE_LOAD)

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
        self._publish_file_selection_after_lazy_data_loaded(SELECTION_SOURCE_LOAD)

    def publish_session_reconnect_restore(self, snapshot: HomePageSessionSnapshot) -> None:
        """Publish one reconnect hydrate event after a hard client rebuild.

        Ensures lazy pixel data stays loaded before views receive
        :class:`HomePageSessionReconnectRestore`.

        Args:
            snapshot: Session snapshot captured on the previous disconnect.

        Returns:
            None.
        """
        self._pending_reconnect_snapshot = snapshot
        self._publish_reconnect_restore_after_lazy_data_loaded()

    def _publish_reconnect_restore_after_lazy_data_loaded(self) -> None:
        """Ensure lazy data is loaded, then publish reconnect restore once.

        Returns:
            None.
        """
        if self._acq_image_data_controller is None:
            self._publish_session_reconnect_restore_event()
            return

        self._acq_image_data_controller.ensure_loaded_for_selection(
            self._state.selection.file_id,
            self._resolved_acq_image_for_selection(),
            on_complete=self._publish_session_reconnect_restore_event,
        )

    def _publish_session_reconnect_restore_event(self) -> None:
        """Publish the reconnect hydrate event from current state and snapshot.

        Returns:
            None.
        """
        snapshot = self._pending_reconnect_snapshot or HomePageSessionSnapshot.empty()
        self._pending_reconnect_snapshot = None
        selection = self._state.selection
        self._event_bus.publish(
            HomePageSessionReconnectRestore(
                file_id=selection.file_id,
                acq_image=self._resolved_acq_image_for_selection(),
                channel=selection.channel,
                roi_id=selection.roi_id,
                analysis_name=selection.analysis_name,
                primary_x_range=self._state.primary_x_range,
                view_session=dict(snapshot.views),
            )
        )

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
            self._publish_file_selection_changed(event.source)
            return

        if self._state.acq_image_list is not None:
            acq_file = self._state.acq_image_list.get_file_by_id(event.file_id)
            if acq_file is None:
                raise ValueError(f'Unknown file_id: {event.file_id!r}')

            channel = event.channel if event.channel is not None else acq_file.get_default_channel()
            roi_id = event.roi_id if event.roi_id is not None else acq_file.get_default_roi()
            self._state.selection = PrimarySelection(
                file_id=acq_file.file_id,
                channel=channel,
                roi_id=roi_id,
                analysis_name=event.analysis_name,
            )
            self._publish_file_selection_after_lazy_data_loaded(event.source)
            return

        if event.file_id not in self._state.file_ids:
            raise ValueError(f'Unknown file_id: {event.file_id!r}')

        self._state.selection.file_id = event.file_id
        self._state.selection.channel = event.channel if event.channel is not None else 0
        self._state.selection.roi_id = event.roi_id
        self._state.selection.analysis_name = event.analysis_name
        self._publish_file_selection_after_lazy_data_loaded(event.source)

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
        self._state.selection.analysis_name = None
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
        self._state.selection.analysis_name = None
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


    def _on_unload_image_data(self, event: UnloadImageDataIntent) -> None:
        """Handle request to unload one file's lazy image/analysis data.

        If the requested file is currently selected, selection is cleared before
        unloading so views transition to the existing "no file selected" state
        and never need to understand lazy-loading state themselves.

        Args:
            event: Unload request carrying a file identifier.

        Raises:
            RuntimeError: If no acquisition list is loaded.
            ValueError: If ``event.file_id`` is unknown.
        """
        if self._state.acq_image_list is None:
            raise RuntimeError('Cannot unload image data without a loaded AcqImageList')
        acq_image = self._state.acq_image_list.get_file_by_id(event.file_id)
        if acq_image is None:
            raise ValueError(f'Unknown file_id: {event.file_id!r}')

        if self._state.selection.file_id == event.file_id:
            self._state.selection = PrimarySelection()
            self._publish_file_selection_changed(SELECTION_SOURCE_EXTERNAL)

        if self._acq_image_data_controller is None:
            acq_image.unload_lazy_data()
            self._event_bus.publish(
                ImageDataUnloaded(
                    file_id=event.file_id,
                    file_list_row=dict(acq_image.get_schema_row()),
                )
            )
            return

        self._acq_image_data_controller.unload_file_data(event.file_id, acq_image)

    def _resolved_acq_image_for_selection(self) -> AcqImage | None:
        """Return the ``AcqImage`` for the current selection when available.

        Returns:
            Matching acquisition object, or ``None``.
        """
        fid = self._state.selection.file_id
        if fid is not None and self._state.acq_image_list is not None:
            return self._state.acq_image_list.get_file_by_id(fid)
        return None

    def _publish_file_selection_after_lazy_data_loaded(self, source: str) -> None:
        """Ensure lazy data is loaded, then publish file selection state once.

        Args:
            source: Selection origin captured for this specific request.

        Returns:
            None.
        """
        if self._acq_image_data_controller is None:
            self._publish_file_selection_changed(source)
            return

        self._acq_image_data_controller.ensure_loaded_for_selection(
            self._state.selection.file_id,
            self._resolved_acq_image_for_selection(),
            on_complete=lambda: self._publish_file_selection_changed(source),
        )

    def _publish_file_selection_changed(self, source: str) -> None:
        """Publish file selection including its explicit origin.

        Args:
            source: Selection origin captured for the published state.

        Returns:
            None.
        """
        acq_image = self._resolved_acq_image_for_selection()
        fid = self._state.selection.file_id
        self._event_bus.publish(
            FileSelectionChanged(
                file_id=fid,
                acq_image=acq_image,
                channel=self._state.selection.channel,
                roi_id=self._state.selection.roi_id,
                analysis_name=self._state.selection.analysis_name,
                source=source,
            )
        )
