"""Analysis workflow controller for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.analysis.batch.acq_analysis_batch import AcqAnalysisBatch
from acqstore.acq_image.analysis.batch.diameter_batch_strategy import DiameterBatchStrategy
from acqstore.acq_image.analysis.batch.radon_velocity_batch_strategy import RadonVelocityBatchStrategy
from acqstore.acq_image.analysis.batch.roi_mode import RoiBatchMode
from acqstore.acq_image.analysis.model import (
    AnalysisExclusionError,
    AnalysisKey,
    AnalysisRunContext,
)
from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import (
    RadonVelocityAnalysis,
)

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisCompleted,
    BatchAnalysisCompleted,
    AnalysisKind,
    CancelTaskIntent,
    RunAnalysisIntent,
    RunBatchAnalysisIntent,
    TaskKind,
)
from cloudscope.events.status import AppStatusChanged, StatusLevel, StatusSource
from cloudscope.state import PrimarySelection
from cloudscope.task_runner import TaskContext, TaskRunner

from cloudscope.utils.logging import get_logger
logger = get_logger(__name__)


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
        self.event_bus.subscribe(RunBatchAnalysisIntent, self._on_run_batch_analysis)
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
            message = f"Analysis could not start: {exc}"
            logger.error(f'{message}')
            self.event_bus.publish(
                AppStatusChanged(
                    level=StatusLevel.ERROR,
                    message=message,
                    source=StatusSource.ANALYSIS,
                )
            )

    def _on_run_batch_analysis(self, event: RunBatchAnalysisIntent) -> None:
        """Start batch analysis for explicit visible file-table rows.

        Args:
            event: Batch run intent carrying an ordered explicit file-id list.

        Returns:
            None.
        """
        try:
            self._validate_batch_intent(event)
            task_label = f"Batch analysis: {event.analysis_kind.value}"
            self.task_runner.start(
                task_kind=TaskKind.ANALYSIS,
                task_label=task_label,
                worker=lambda context: self._run_batch_analysis_worker(event, context),
                on_completed=lambda _result: self._publish_batch_analysis_completed(event, success=True, message="Batch analysis complete"),
                on_failed=lambda exc: self._publish_batch_analysis_completed(event, success=False, message=str(exc)),
                on_cancelled=lambda: self._publish_batch_analysis_completed(event, success=False, message="Batch analysis cancelled"),
            )
        except Exception as exc:
            message = f"Batch analysis could not start: {exc}"
            logger.error(f'{message}')
            self.event_bus.publish(
                AppStatusChanged(
                    level=StatusLevel.ERROR,
                    message=message,
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
        if event.analysis_kind not in (
            AnalysisKind.RADON_VELOCITY,
            AnalysisKind.DIAMETER,
            AnalysisKind.EVENT,
        ):
            raise NotImplementedError(f"Unsupported analysis kind: {event.analysis_kind}")
        if event.analysis_kind is not AnalysisKind.EVENT:
            self._raise_if_exclusive_conflict(event)

    def _validate_batch_intent(self, event: RunBatchAnalysisIntent) -> None:
        """Validate that a batch analysis intent can start.

        Args:
            event: Batch run intent.

        Raises:
            ValueError: If required fields are missing.
            RuntimeError: If no acquisition image list is loaded.
            NotImplementedError: If the analysis kind is unsupported.
        """
        if not event.file_ids:
            raise ValueError("No visible table rows to analyze")
        if self.home_controller.state.acq_image_list is None:
            raise RuntimeError("No AcqImageList loaded")
        if event.analysis_kind not in (AnalysisKind.RADON_VELOCITY, AnalysisKind.DIAMETER):
            raise NotImplementedError(f"Unsupported batch analysis kind: {event.analysis_kind}")
        for file_id in event.file_ids:
            acq_image = self.home_controller.state.acq_image_list.get_file_by_id(file_id)
            if acq_image is None:
                raise RuntimeError(f"Visible file is no longer loaded: {file_id!r}")
            self._raise_if_exclusive_conflict_for_values(
                acq_image=acq_image,
                analysis_name=event.analysis_kind.value,
                channel=int(event.channel),
                roi_id=int(event.roi_id),
            )

    def _raise_if_exclusive_conflict(self, event: RunAnalysisIntent) -> None:
        """Reject the intent when an exclusive-group conflict would occur.

        Args:
            event: Run-analysis intent.

        Raises:
            AnalysisExclusionError: If a conflicting primary-kymograph analysis
                already exists for the same (channel, roi_id).
        """
        selection = event.selection
        if selection.file_id is None or selection.channel is None or selection.roi_id is None:
            return
        acq_image_list = self.home_controller.state.acq_image_list
        if acq_image_list is None:
            return
        acq_image = acq_image_list.get_file_by_id(selection.file_id)
        if acq_image is None:
            return
        self._raise_if_exclusive_conflict_for_values(
            acq_image=acq_image,
            analysis_name=event.analysis_kind.value,
            channel=int(selection.channel),
            roi_id=int(selection.roi_id),
        )

    def _raise_if_exclusive_conflict_for_values(
        self,
        *,
        acq_image: object,
        analysis_name: str,
        channel: int,
        roi_id: int,
    ) -> None:
        """Raise when a primary-kymograph conflict exists for concrete values.

        Args:
            acq_image: Acquisition image containing an analysis set.
            analysis_name: Analysis name requested for the run.
            channel: Channel index.
            roi_id: ROI identifier.

        Raises:
            AnalysisExclusionError: If a different primary-kymograph analysis is
                already present for ``(channel, roi_id)``.
        """
        existing = acq_image.analysis_set.get_primary_kymograph_analysis(
            channel=int(channel),
            roi_id=int(roi_id),
        )
        if existing is None or existing.key.analysis_name == analysis_name:
            return
        raise AnalysisExclusionError(
            f"Cannot run {analysis_name!r}: {existing.key.analysis_name!r} already "
            f"exists for channel={channel}, roi_id={roi_id}. "
            "Remove the existing analysis first."
        )

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
        if event.analysis_kind is AnalysisKind.EVENT:
            analysis = acq_image.analysis_set.get(key)
            if analysis is None:
                analysis = acq_image.analysis_set.create(
                    event.analysis_kind.value,
                    channel=channel,
                    roi_id=roi_id,
                    detection_params=dict(event.detection_params),
                )
            elif not isinstance(analysis, EventAnalysis):
                raise TypeError(f"Expected EventAnalysis, got {type(analysis).__name__}")
            else:
                analysis.set_detection_params(dict(event.detection_params))
        else:
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
        if isinstance(analysis, RadonVelocityAnalysis):
            self._rerun_dependent_event_analysis(acq_image, channel=channel, roi_id=roi_id, context=run_context)
        context.report_progress(1.0, "Analysis complete")

    def _run_batch_analysis_worker(self, event: RunBatchAnalysisIntent, context: TaskContext) -> None:
        """Run batch analysis for explicit visible file-table rows.

        Args:
            event: Batch intent carrying the ordered file ids to process.
            context: Task runner context for progress/cancellation.

        Returns:
            None.

        Raises:
            RuntimeError: If any file id can no longer be resolved.
        """
        acq_image_list = self.home_controller.state.acq_image_list
        if acq_image_list is None:
            raise RuntimeError("No AcqImageList loaded")

        files = []
        for file_id in event.file_ids:
            acq_image = acq_image_list.get_file_by_id(file_id)
            if acq_image is None:
                raise RuntimeError(f"Visible file is no longer loaded: {file_id!r}")
            files.append(acq_image)

        context.report_progress(0.0, f"Preparing {len(files)} files")
        context.raise_if_cancelled()
        strategy = self._batch_strategy_for_event(event)
        cancel_event = context.cancel_event
        completed = 0
        total = len(files)

        def _on_file_result(result: object) -> None:
            nonlocal completed
            completed += 1
            context.report_progress(completed / total, f"{completed}/{total}: {result}")

        batch = AcqAnalysisBatch(files, strategy, max_parallel_files=1)
        batch.run(cancel_event=cancel_event, on_file_result=_on_file_result)
        if context.is_cancelled() or cancel_event.is_set():
            context.raise_if_cancelled()
        context.report_progress(1.0, "Batch analysis complete")

    def _batch_strategy_for_event(self, event: RunBatchAnalysisIntent) -> object:
        """Build the AcqStore batch strategy for a CloudScope batch intent.

        Args:
            event: Batch run intent.

        Returns:
            Backend batch strategy instance.

        Raises:
            NotImplementedError: If the analysis kind is unsupported.
        """
        common = dict(
            channel=int(event.channel),
            roi_mode=RoiBatchMode.ANALYZE_EXISTING_ROI,
            roi_id=int(event.roi_id),
            detection_params=dict(event.detection_params),
        )
        if event.analysis_kind is AnalysisKind.RADON_VELOCITY:
            return RadonVelocityBatchStrategy(**common, use_multiprocessing=True)
        if event.analysis_kind is AnalysisKind.DIAMETER:
            return DiameterBatchStrategy(**common, use_threads=True)
        raise NotImplementedError(f"Unsupported batch analysis kind: {event.analysis_kind}")

    def _rerun_dependent_event_analysis(
        self,
        acq_image: object,
        *,
        channel: int,
        roi_id: int,
        context: AnalysisRunContext,
    ) -> None:
        """Rerun existing event analysis after parent Radon velocity changes.

        Args:
            acq_image: Selected acquisition image containing an analysis set.
            channel: Channel index.
            roi_id: ROI identifier.
            context: Analysis run context.

        Returns:
            None.
        """
        key = AnalysisKey(AnalysisKind.EVENT.value, channel, roi_id)
        event_analysis = acq_image.analysis_set.get(key)
        if event_analysis is None:
            return
        if not isinstance(event_analysis, EventAnalysis):
            raise TypeError(f"Expected EventAnalysis, got {type(event_analysis).__name__}")
        context.report_progress(None, "Refreshing event statistics")
        acq_image.analysis_set.run_analysis(key, context=context)

    def _publish_batch_analysis_completed(
        self,
        event: RunBatchAnalysisIntent,
        *,
        success: bool,
        message: str,
    ) -> None:
        """Publish batch completion and row-refresh events.

        Args:
            event: Original batch intent.
            success: Whether the batch completed successfully.
            message: Human-readable message.

        Returns:
            None.
        """
        self.event_bus.publish(
            BatchAnalysisCompleted(
                analysis_kind=event.analysis_kind,
                file_ids=tuple(event.file_ids),
                channel=int(event.channel),
                roi_id=int(event.roi_id),
                success=success,
                message=message,
            )
        )
        for file_id in event.file_ids:
            self.event_bus.publish(
                AnalysisCompleted(
                    analysis_kind=event.analysis_kind,
                    selection=PrimarySelection(
                        file_id=file_id,
                        channel=int(event.channel),
                        roi_id=int(event.roi_id),
                    ),
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
