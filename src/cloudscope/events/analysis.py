"""Primary analysis run/cancel/progress/completion and plot interaction state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from acqstore.acq_image.analysis.batch.roi_mode import RoiBatchMode
from acqstore.acq_image.analysis.batch.types import BatchFileResult
from cloudscope.events.base import IntentEvent, StateEvent
from cloudscope.state import PrimarySelection


class TaskKind(StrEnum):
    """Supported long-running task categories."""

    LOAD = 'load'
    SAVE = 'save'
    ANALYSIS = 'analysis'
    BATCH_ANALYSIS = 'batch_analysis'


class AnalysisKind(StrEnum):
    """Supported CloudScope analysis kinds."""

    RADON_VELOCITY = 'radon_velocity'
    DIAMETER = 'diameter'
    EVENT = 'event'


class TaskStatus(StrEnum):
    """Lifecycle states for progress events."""

    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


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
class RunBatchAnalysisIntent(IntentEvent):
    """Request to run one analysis over explicit file-table rows.

    Args:
        batch_id: Unique id used to correlate per-file and final batch events.
        analysis_kind: Analysis kind to run.
        file_ids: Ordered file identifiers captured from the visible, filtered,
            sorted file table rows. The backend must not expand this list.
        channel: Channel index used for every file.
        roi_mode: How each file's target ROI is selected.
        roi_id: ROI identifier for ``ANALYZE_EXISTING_ROI`` mode, otherwise None.
        detection_params: Analysis detection parameters keyed by schema field name.
    """

    batch_id: str
    analysis_kind: AnalysisKind
    file_ids: tuple[str, ...]
    channel: int
    roi_mode: RoiBatchMode
    roi_id: int | None
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
class BatchFileAnalysisCompleted(StateEvent):
    """Emitted when one file finishes during a batch analysis task.

    Args:
        batch_id: Batch id from the original run intent.
        analysis_kind: Analysis kind that ran.
        file_id: File identifier for the completed row.
        result: Per-file backend batch result.
    """

    batch_id: str
    analysis_kind: AnalysisKind
    file_id: str
    result: BatchFileResult


@dataclass(frozen=True)
class BatchAnalysisCompleted(StateEvent):
    """Emitted when a batch analysis task reaches a terminal state.

    Args:
        batch_id: Batch id from the original run intent.
        analysis_kind: Analysis kind that ran.
        file_ids: Ordered file identifiers requested by the batch intent.
        channel: Channel index used for every file.
        roi_mode: How each file's target ROI was selected.
        roi_id: ROI identifier for ``ANALYZE_EXISTING_ROI`` mode, otherwise None.
        results: Per-file backend batch results collected before completion.
        success: True when the batch completed without task failure.
        message: Human-readable completion, cancellation, or error message.
    """

    batch_id: str
    analysis_kind: AnalysisKind
    file_ids: tuple[str, ...]
    channel: int
    roi_mode: RoiBatchMode
    roi_id: int | None
    results: tuple[BatchFileResult, ...]
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
