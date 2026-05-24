"""
Event definitions for CloudScope.

Events are split into:
- Intent events (user or system requests)
- State events (facts after mutation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from cloudscope.state import PrimarySelection

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


class Event:
    """Base event."""


class IntentEvent(Event):
    """Base class for intent events."""


class StateEvent(Event):
    """Base class for state events."""


class LoadPathKind(StrEnum):
    """Supported source kinds for load intents."""

    FILE = 'file'
    FOLDER = 'folder'
    CSV = 'csv'


class TaskKind(StrEnum):
    """Supported long-running task categories."""

    LOAD = 'load'
    SAVE = 'save'
    ANALYSIS = 'analysis'


class AnalysisKind(StrEnum):
    """Supported CloudScope analysis kinds."""

    RADON_VELOCITY = 'radon_velocity'
    DIAMETER = 'diameter'
    EVENT = 'event'


class RoiChangeKind(StrEnum):
    """Supported ROI model mutation kinds."""

    ADD = 'add'
    DELETE = 'delete'
    EDIT = 'edit'


class TaskStatus(StrEnum):
    """Lifecycle states for progress events."""

    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class StatusLevel(StrEnum):
    """UI status severity level."""

    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


class StatusSource(StrEnum):
    """Subsystem source for a status message."""

    LOAD = 'load'
    SAVE = 'save'
    ANALYSIS = 'analysis'
    SYSTEM = 'system'


# -----------------------------
# Intent Events
# -----------------------------

@dataclass(frozen=True)
class SelectFileIntent(IntentEvent):
    """Request to select a file."""
    file_id: str | None


@dataclass(frozen=True)
class SelectChannelIntent(IntentEvent):
    """Request to select a channel."""
    channel: int | None


@dataclass(frozen=True)
class SelectRoiIntent(IntentEvent):
    """Request to select an ROI."""
    roi_id: int | None


@dataclass(frozen=True)
class ResetHomeLayoutIntent(IntentEvent):
    """Request resetting Home page splitters to factory defaults."""


@dataclass(frozen=True)
class SetHomeViewVisibleIntent(IntentEvent):
    """Request changing visibility for a configurable Home page view.

    Args:
        view_id: Stable view id string.
        visible: Desired visibility.
    """

    view_id: str
    visible: bool


@dataclass(frozen=True)
class AddRoiIntent(IntentEvent):
    """Request creation of a new ROI for a selection snapshot.

    Args:
        selection: File/channel/ROI snapshot captured at user click time.
            ``selection.roi_id`` may be None because the controller creates the
            new ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class DeleteRoiIntent(IntentEvent):
    """Request deletion of an existing ROI.

    Args:
        selection: File/channel/ROI snapshot identifying the ROI to delete.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class BeginEditRoiIntent(IntentEvent):
    """Request entry into ROI edit mode for a selection snapshot.

    Args:
        selection: File/channel/ROI snapshot identifying the ROI to edit.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class CancelEditRoiIntent(IntentEvent):
    """Request cancellation of the current ROI edit mode.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI when
            available.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class SubmitEditRoiIntent(IntentEvent):
    """Request submission of ROI edits for a selection snapshot.

    Geometry editing is not implemented in this milestone. The event is kept as
    the controller-facing contract for the toolbar OK action.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class ApplyRoiFullWidthIntent(IntentEvent):
    """Request full-width ROI adjustment while editing.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class ApplyRoiFullHeightIntent(IntentEvent):
    """Request full-height ROI adjustment while editing.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class ApplyMetadataIntent(IntentEvent):
    """Request to apply edited metadata for one file section (in-memory only)."""

    file_id: str
    metadata_section_id: str
    patch: dict[str, object]


@dataclass(frozen=True)
class LoadPathIntent(IntentEvent):
    """Request to load files from a path source."""

    path: str
    kind: LoadPathKind
    from_recent: bool = False


@dataclass(frozen=True)
class RemoveRecentPathIntent(IntentEvent):
    """Remove one path from recent files or recent folders (e.g. stale menu pick)."""

    path: str
    kind: LoadPathKind


@dataclass(frozen=True)
class ClearRecentPathsIntent(IntentEvent):
    """Request to clear recent file and folder paths."""


@dataclass(frozen=True)
class SaveSelectedIntent(IntentEvent):
    """Request to save currently selected file."""


@dataclass(frozen=True)
class SaveAllIntent(IntentEvent):
    """Request to save all dirty files."""


@dataclass(frozen=True)
class RunAnalysisIntent(IntentEvent):
    """Request to run one analysis for a selection snapshot.

    Args:
        analysis_kind: Analysis kind to run.
        selection: File/channel/ROI snapshot captured at user click time.
        detection_params: Analysis detection parameters keyed by schema field name.
    """

    analysis_kind: AnalysisKind
    selection: PrimarySelection
    detection_params: dict[str, object]


@dataclass(frozen=True)
class CancelTaskIntent(IntentEvent):
    """Request cancellation of a running task.

    Args:
        task_kind: Task category to cancel.
        task_id: Optional task identifier. If omitted, the active task of the
            requested kind is cancelled.
    """

    task_kind: TaskKind
    task_id: str | None = None


@dataclass(frozen=True)
class BeginAddAcqImageEventIntent(IntentEvent):
    """Request one-shot x-range selection to create an AcqImage event.

    Args:
        selection: Selection snapshot for the target event analysis.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class CancelAddAcqImageEventIntent(IntentEvent):
    """Request cancellation of pending AcqImage event creation."""


@dataclass(frozen=True)
class AcqImageEventXRangeSelectedIntent(IntentEvent):
    """Report a user-selected x-range for event creation.

    Args:
        selection: Selection snapshot associated with the plotted analysis.
        x0: First x coordinate.
        x1: Second x coordinate.
    """

    selection: PrimarySelection
    x0: float
    x1: float


@dataclass(frozen=True)
class DeleteSelectedAcqImageEventIntent(IntentEvent):
    """Request deletion of the selected AcqImage event."""


@dataclass(frozen=True)
class SelectAcqImageEventIntent(IntentEvent):
    """Request selection of an AcqImage event.

    Args:
        event_id: Event id to select, or None to clear selection.
    """

    event_id: int | None


@dataclass(frozen=True)
class SetAcqImageEventsVisibleIntent(IntentEvent):
    """Request event overlay visibility change.

    Args:
        visible: True to show event overlays.
    """

    visible: bool


@dataclass(frozen=True)
class RequestAcqImageEventsRefreshIntent(IntentEvent):
    """Request current AcqImage event rows for one selection.

    Views emit this when a selection changes or when a hidden event view is
    shown again. The controller remains the only object that reads the
    AcqImage event analysis and publishes table/overlay state.

    Args:
        selection: Selection snapshot to refresh.
    """

    selection: PrimarySelection


# -----------------------------
# State Events
# -----------------------------

@dataclass(frozen=True)
class FileListChanged(StateEvent):
    """Emitted when the current file list changes.

    Attributes:
        file_ids: Stable file identifiers in display order.
        rows: Current table rows keyed by schema field names.
    """
    file_ids: list[str]
    rows: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class FileSelectionChanged(StateEvent):
    """Emitted when the selected file changes (including initial list load).

    Initial load and file switches publish this event only (not separate
    channel/ROI events); ``channel`` and ``roi_id`` carry the effective defaults
    for the selected file.

    Attributes:
        file_id: Selected file identifier, or ``None`` if nothing is selected.
        acq_image: Resolved ``AcqImage`` when a list is loaded, else ``None``
            (e.g. demo file ids without backend objects).
        channel: Default or current channel for ``file_id``.
        roi_id: Default or current ROI for ``file_id``.
    """

    file_id: str | None
    acq_image: AcqImage | None
    channel: int | None
    roi_id: int | None


@dataclass(frozen=True)
class ChannelSelectionChanged(StateEvent):
    """Emitted when the selected channel changes without a file change.

    Attributes:
        channel: Selected channel index, or ``None`` if cleared.
    """

    channel: int | None


@dataclass(frozen=True)
class RoiSelectionChanged(StateEvent):
    """Emitted when the selected ROI changes without a file change.

    Attributes:
        roi_id: Selected ROI identifier, or ``None`` if cleared.
    """

    roi_id: int | None


@dataclass(frozen=True)
class RoiChanged(StateEvent):
    """Emitted after ROI model state changes for one file.

    The model is authoritative. Views should use this event as a signal to pull
    fresh ROI/table/analysis state from ``AppState`` and the selected
    ``AcqImage``.

    Args:
        operation: ROI mutation kind.
        selection: Selection snapshot after the ROI mutation. For add this
            contains the new ROI id. For delete this contains the next selected
            ROI id, or None when no ROI remains.
        removed_analysis_count: Number of dependent analyses removed because of
            the ROI mutation.
    """

    operation: RoiChangeKind
    selection: PrimarySelection
    removed_analysis_count: int = 0


@dataclass(frozen=True)
class RoiEditModeChanged(StateEvent):
    """Emitted when ROI edit mode starts or ends.

    Args:
        is_editing: True while the app is in ROI edit mode.
        selection: ROI edit selection snapshot, or None when edit mode exits.
        message: User-visible status text.
    """

    is_editing: bool
    selection: PrimarySelection | None
    message: str = ''


@dataclass(frozen=True)
class MetadataChanged(StateEvent):
    """Emitted after metadata values were applied for one file.

    ``file_list_row`` is a shallow snapshot: keys match ``ACQ_FILE_LIST_SCHEMA`` exactly.
    """

    file_id: str
    metadata_section_id: str
    file_list_row: dict[str, object]


@dataclass(frozen=True)
class TaskProgressChanged(StateEvent):
    """Unified progress state for long-running tasks."""

    task_kind: TaskKind
    task_id: str
    task_label: str
    status: TaskStatus
    current: int
    total: int
    message: str


@dataclass(frozen=True)
class AppBusyChanged(StateEvent):
    """Emitted when the app enters or leaves a long-running task state.

    Args:
        is_busy: True while a task is running.
        task_kind: Running task kind, or None when no task is active.
        task_id: Running task id, or None when no task is active.
        message: Human-readable task message.
    """

    is_busy: bool
    task_kind: TaskKind | None
    task_id: str | None
    message: str


@dataclass(frozen=True)
class AnalysisCompleted(StateEvent):
    """Emitted when an analysis task reaches a terminal state.

    Args:
        analysis_kind: Analysis kind that ran.
        selection: Selection snapshot used by the analysis.
        success: True when analysis completed successfully.
        message: Human-readable completion, cancellation, or error message.
    """

    analysis_kind: AnalysisKind
    selection: PrimarySelection
    success: bool
    message: str = ''


@dataclass(frozen=True)
class BeginPlotXRangeSelection(StateEvent):
    """Request the plot view to enter x-range selection mode.

    Args:
        selection: Selection snapshot that should receive the selected range.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class CancelPlotXRangeSelection(StateEvent):
    """Request the plot view to leave x-range selection mode."""


@dataclass(frozen=True)
class AcqImageEventsChanged(StateEvent):
    """Emitted after AcqImage event model changes.

    Args:
        selection: Selection snapshot for the event analysis.
        rows: Table rows representing current events.
        selected_event_id: Selected event id, if any.
        visible: Whether plot overlays should be visible.
    """

    selection: PrimarySelection
    rows: list[dict[str, object]] = field(default_factory=list)
    selected_event_id: int | None = None
    visible: bool = True


@dataclass(frozen=True)
class AcqImageEventSelectionChanged(StateEvent):
    """Emitted when selected AcqImage event id changes.

    Args:
        selected_event_id: Selected event id, if any.
    """

    selected_event_id: int | None


@dataclass(frozen=True)
class AcqImageEventsVisibilityChanged(StateEvent):
    """Emitted when event overlay visibility changes.

    Args:
        visible: Whether plot overlays should be visible.
    """

    visible: bool


@dataclass(frozen=True)
class AppStatusChanged(StateEvent):
    """Latest app-level status message for footer/notifications."""

    level: StatusLevel
    message: str
    source: StatusSource


@dataclass(frozen=True)
class RecentPathsChanged(StateEvent):
    """Current recent file and folder paths after updates/clear."""

    recent_files: list[str]
    recent_folders: list[str]
