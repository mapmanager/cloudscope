"""Controller logic for the CloudScope home page."""

from __future__ import annotations

from dataclasses import dataclass

from .event_bus import EventBus
from .events import (
    FileListChanged,
    IntentEvent,
    PrimarySelectionChanged,
    SelectChannelIntent,
    SelectFileIntent,
    SelectRoiIntent,
    StateEvent,
)
from .state import PrimarySelection


@dataclass(slots=True)
class HomePageState:
    """Application state for the CloudScope home page.

    Attributes:
        file_ids: Stable file identifiers in display order.
        selection: Current primary selection state.
    """

    file_ids: list[str]
    selection: PrimarySelection


class HomePageController:
    """Coordinate intent events and publish resulting state events.

    This controller owns mutation of page-level state. Views should publish
    intent events and subscribe to state events instead of directly mutating
    shared state or calling each other.
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
        )

    @property
    def state(self) -> HomePageState:
        """Return the current controller state."""
        return self._state

    def bind(self) -> None:
        """Subscribe controller handlers to intent events."""
        self._event_bus.subscribe(SelectFileIntent, self._on_select_file)
        self._event_bus.subscribe(SelectChannelIntent, self._on_select_channel)
        self._event_bus.subscribe(SelectRoiIntent, self._on_select_roi)

    def load_demo_files(self, file_ids: list[str]) -> None:
        """Replace the current file list with demo data.

        Args:
            file_ids: File identifiers in display order.
        """
        self._state.file_ids = list(file_ids)
        self._event_bus.publish(FileListChanged(file_ids=list(self._state.file_ids)))

        default_file_id = self._state.file_ids[0] if self._state.file_ids else None
        self._state.selection = PrimarySelection(
            file_id=default_file_id,
            channel=0 if default_file_id is not None else None,
            roi_id=None,
        )
        self._publish_selection_changed()

    def _on_select_file(self, event: SelectFileIntent) -> None:
        """Handle file selection changes.

        Args:
            event: Requested file selection intent.
        """
        if event.file_id is not None and event.file_id not in self._state.file_ids:
            raise ValueError(f"Unknown file_id: {event.file_id!r}")

        self._state.selection.file_id = event.file_id
        self._state.selection.channel = 0 if event.file_id is not None else None
        self._state.selection.roi_id = None
        self._publish_selection_changed()

    def _on_select_channel(self, event: SelectChannelIntent) -> None:
        """Handle channel selection changes.

        Args:
            event: Requested channel selection intent.
        """
        if self._state.selection.file_id is None and event.channel is not None:
            raise ValueError("Cannot select a channel without a selected file")

        self._state.selection.channel = event.channel
        self._publish_selection_changed()

    def _on_select_roi(self, event: SelectRoiIntent) -> None:
        """Handle ROI selection changes.

        Args:
            event: Requested ROI selection intent.
        """
        if self._state.selection.file_id is None and event.roi_id is not None:
            raise ValueError("Cannot select an ROI without a selected file")

        self._state.selection.roi_id = event.roi_id
        self._publish_selection_changed()

    def _publish_selection_changed(self) -> None:
        """Publish the current primary selection state."""
        self._event_bus.publish(
            PrimarySelectionChanged(
                file_id=self._state.selection.file_id,
                channel=self._state.selection.channel,
                roi_id=self._state.selection.roi_id,
            )
        )
