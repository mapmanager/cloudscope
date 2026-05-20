"""Analysis workflow controller for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisRunContext
from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import (
    RadonVelocityAnalysis,
)

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AnalysisCompleted,
    AnalysisKind,
    AppStatusChanged,
    CancelTaskIntent,
    RunAnalysisIntent,
    StatusLevel,
    StatusSource,
    TaskKind,
)
from cloudscope.state import PrimarySelection
from cloudscope.task_runner import TaskContext, TaskRunner


@dataclass(slots=True)
class AnalysisController:
    """Coordinate analysis intents and background analysis execution.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: State-owner controller used to resolve selected files.
        task_runner: Single-active-task runner used for background work.
    """

    event_bus: EventBus
    home_controller: HomePageController
    task_runner: TaskRunner

    def bind(self) -> None:
        """Subscribe controller handlers to analysis intents.

        Returns:
            None.
        """
        self.event_bus.subscribe(RunAnalysisIntent, self._on_run_analysis)
        self.event_bus.subscribe(CancelTaskIntent, self._on_cancel_task)

    def _on_run_analysis(self, event: RunAnalysisIntent) -> None:
        """Start analysis for one selection snapshot.

        Args:
            event: Run-analysis intent.

        Returns:
            None.
        """
        try:
            self._validate_intent(event)
            task_label = f"Analysis: {event.analysis_kind.value}"
            self.task_runner.start(
                task_kind=TaskKind.ANALYSIS,
                task_label=task_label,
                worker=lambda context: self._run_analysis_worker(event, context),
                on_completed=lambda _result: self._publish_analysis_completed(event, success=True, message="Analysis complete"),
                on_failed=lambda exc: self._publish_analysis_completed(event, success=False, message=str(exc)),
                on_cancelled=lambda: self._publish_analysis_completed(event, success=False, message="Analysis cancelled"),
            )
        except Exception as exc:
            self.event_bus.publish(
                AppStatusChanged(
                    level=StatusLevel.ERROR,
                    message=f"Analysis could not start: {exc}",
                    source=StatusSource.ANALYSIS,
                )
            )

    def _on_cancel_task(self, event: CancelTaskIntent) -> None:
        """Cancel analysis task intents.

        Args:
            event: Cancel-task intent.

        Returns:
            None.
        """
        if event.task_kind is not TaskKind.ANALYSIS:
            return
        cancelled = self.task_runner.cancel(task_kind=TaskKind.ANALYSIS, task_id=event.task_id)
        if not cancelled:
            self.event_bus.publish(
                AppStatusChanged(
                    level=StatusLevel.WARNING,
                    message="No running analysis task to cancel",
                    source=StatusSource.ANALYSIS,
                )
            )

    def _validate_intent(self, event: RunAnalysisIntent) -> None:
        """Validate that an analysis intent can start.

        Args:
            event: Run-analysis intent.

        Raises:
            ValueError: If required selection fields are missing.
            RuntimeError: If no acquisition image list is loaded.
            NotImplementedError: If the analysis kind is unsupported.
        """
        selection = event.selection
        if selection.file_id is None:
            raise ValueError("No file selected")
        if selection.channel is None:
            raise ValueError("No channel selected")
        if selection.roi_id is None:
            raise ValueError("No ROI selected")
        if self.home_controller.state.acq_image_list is None:
            raise RuntimeError("No AcqImageList loaded")
        if event.analysis_kind not in (AnalysisKind.RADON_VELOCITY, AnalysisKind.DIAMETER):
            raise NotImplementedError(f"Unsupported analysis kind: {event.analysis_kind}")

    def _run_analysis_worker(self, event: RunAnalysisIntent, context: TaskContext) -> None:
        """Run one analysis in a background worker thread.

        Args:
            event: Analysis intent containing immutable-enough selection snapshot.
            context: Task runner context for progress/cancellation.

        Returns:
            None.

        Raises:
            RuntimeError: If the selected file cannot be resolved.
            ValueError: If selection fields are missing.
        """
        selection = event.selection
        file_id, channel, roi_id = self._required_selection_values(selection)
        acq_image_list = self.home_controller.state.acq_image_list
        if acq_image_list is None:
            raise RuntimeError("No AcqImageList loaded")
        acq_image = acq_image_list.get_file_by_id(file_id)
        if acq_image is None:
            raise RuntimeError(f"Selected file is no longer loaded: {file_id!r}")

        context.report_progress(0.0, "Preparing analysis")
        context.raise_if_cancelled()
        key = AnalysisKey(event.analysis_kind.value, channel, roi_id)
        acq_image.analysis_set.remove(key)
        analysis = acq_image.analysis_set.create(
            event.analysis_kind.value,
            channel=channel,
            roi_id=roi_id,
            detection_params=dict(event.detection_params),
        )
        if isinstance(analysis, RadonVelocityAnalysis):
            analysis.set_execution_options(use_multiprocessing=True)
        elif isinstance(analysis, DiameterAnalysis):
            analysis.set_execution_options(use_threads=True)

        run_context = AnalysisRunContext(
            progress_callback=context.report_progress,
            cancel_callback=context.is_cancelled,
        )
        acq_image.analysis_set.run_analysis(analysis.key, context=run_context)
        context.report_progress(1.0, "Analysis complete")

    def _publish_analysis_completed(
        self,
        event: RunAnalysisIntent,
        *,
        success: bool,
        message: str,
    ) -> None:
        """Publish analysis completion and status events.

        Args:
            event: Original analysis intent.
            success: Whether analysis completed successfully.
            message: Human-readable message.

        Returns:
            None.
        """
        self.event_bus.publish(
            AnalysisCompleted(
                analysis_kind=event.analysis_kind,
                selection=self._copy_selection(event.selection),
                success=success,
                message=message,
            )
        )
        self.event_bus.publish(
            AppStatusChanged(
                level=StatusLevel.INFO if success else StatusLevel.WARNING,
                message=message,
                source=StatusSource.ANALYSIS,
            )
        )

    @staticmethod
    def _copy_selection(selection: PrimarySelection) -> PrimarySelection:
        """Return a copied primary selection.

        Args:
            selection: Selection to copy.

        Returns:
            Copied selection.
        """
        return PrimarySelection(
            file_id=selection.file_id,
            channel=selection.channel,
            roi_id=selection.roi_id,
        )

    @staticmethod
    def _required_selection_values(selection: PrimarySelection) -> tuple[str, int, int]:
        """Return non-None selection values.

        Args:
            selection: Selection to validate.

        Returns:
            Tuple of ``(file_id, channel, roi_id)``.

        Raises:
            ValueError: If any required value is missing.
        """
        if selection.file_id is None:
            raise ValueError("No file selected")
        if selection.channel is None:
            raise ValueError("No channel selected")
        if selection.roi_id is None:
            raise ValueError("No ROI selected")
        return (selection.file_id, selection.channel, selection.roi_id)
