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
    SUM_INTENSITY = 'sum_intensity'


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
class AnalysisChanged(StateEvent):
    """Emitted when an analysis model changes outside a run task.

    Direct mutations such as event CRUD update an existing analysis object
    without going through ``RunAnalysisIntent``. Controllers publish this event
    after those mutations so downstream model caches can refresh the affected
    row.

    Args:
        analysis_kind: Analysis kind that changed.
        selection: Selection snapshot identifying the affected analysis.
        message: Optional human-readable message.
    """

    analysis_kind: AnalysisKind
    selection: PrimarySelection
    message: str = ''


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


class AnalysisUiMode(StrEnum):
    """Modal analysis UI modes that freeze most of the GUI via app-busy."""

    SET_F0 = 'set_f0'


@dataclass(frozen=True)
class BeginAnalysisUiModeIntent(IntentEvent):
    """Request entry into a modal analysis UI mode.

    The analysis controller publishes ``AppBusyChanged(is_busy=True)`` and
    ``AnalysisUiModeChanged`` when the mode starts successfully.

    Args:
        analysis_kind: Analysis kind that owns the mode.
        mode: Stable mode identifier (for example ``AnalysisUiMode.SET_F0``).
        selection: File/channel/ROI snapshot for the interaction.
    """

    analysis_kind: AnalysisKind
    mode: AnalysisUiMode
    selection: PrimarySelection


@dataclass(frozen=True)
class CancelAnalysisUiModeIntent(IntentEvent):
    """Request exit from a modal analysis UI mode without committing params.

    Args:
        analysis_kind: Analysis kind that owns the active mode.
        mode: Mode identifier to cancel.
        selection: Selection snapshot from the requesting view.
    """

    analysis_kind: AnalysisKind
    mode: AnalysisUiMode
    selection: PrimarySelection


@dataclass(frozen=True)
class AnalysisUiModeChanged(StateEvent):
    """Emitted when a modal analysis UI mode starts or ends.

    Args:
        is_active: True while the mode is active.
        analysis_kind: Analysis kind that owns the mode, or None when inactive.
        mode: Active mode identifier, or None when inactive.
        selection: Selection for the active mode, or None when inactive.
        message: Optional user-visible status text.
    """

    is_active: bool
    analysis_kind: AnalysisKind | None
    mode: AnalysisUiMode | None
    selection: PrimarySelection | None
    message: str = ''


@dataclass(frozen=True)
class UpdateAnalysisDetectionParamsIntent(IntentEvent):
    """Request a partial update of analysis detection parameters (draft UI).

    Controllers validate ``param_updates`` against the analysis schema and
    publish ``AnalysisDetectionParamsChanged`` on success. When
    ``run_analysis`` is True, the controller merges the patch onto the
    last-run detection params for the selection and starts the same analysis
    path as :class:`RunAnalysisIntent`.

    Args:
        analysis_kind: Target analysis kind.
        selection: Selection the update applies to.
        param_updates: Partial schema-keyed values (Edit F0 Set Manual sends
            ``baseline_method`` and ``manual_f0_baseline``; Set Auto sends
            ``baseline_method`` and ``baseline_percentile``).
        run_analysis: When True, run analysis after accepting the draft update.
    """

    analysis_kind: AnalysisKind
    selection: PrimarySelection
    param_updates: dict[str, object]
    run_analysis: bool = False


@dataclass(frozen=True)
class AnalysisDetectionParamsChanged(StateEvent):
    """Detection-parameter draft values were accepted for one analysis kind.

    Views that own detection-parameter controls apply ``param_updates``.
    This is not a run-completion signal.

    Args:
        analysis_kind: Analysis kind whose draft params changed.
        selection: Selection the update applies to.
        param_updates: Partial schema-keyed values that were accepted.
    """

    analysis_kind: AnalysisKind
    selection: PrimarySelection
    param_updates: dict[str, object]
