"""Tests for centralized sum-intensity-pool runtime maintenance."""

from __future__ import annotations

from dataclasses import dataclass, field

from acqstore.acq_image.analysis.batch.types import BatchFileOutcome, BatchFileResult
from cloudscope.controllers.sum_intensity_pool_controller import SumIntensityPoolController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisChanged,
    AnalysisCompleted,
    AnalysisKind,
    BatchFileAnalysisCompleted,
)
from cloudscope.events.files import FileListChanged
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.events.sum_intensity_pool import (
    SumIntensityPoolChanged,
    SumIntensityPoolChangeKind,
)
from cloudscope.state import PrimarySelection


@dataclass
class FakeSumIntensityPool:
    """Fake backend pool recording mutations."""

    calls: list[tuple[str, object]] = field(default_factory=list)

    def rebuild(self) -> None:
        self.calls.append(("rebuild", None))

    def refresh_rows(self, file_id: str, *, channel: int, roi_id: int) -> None:
        self.calls.append(("refresh_rows", (file_id, channel, roi_id)))

    def remove_roi(self, file_id: str, *, roi_id: int) -> None:
        self.calls.append(("remove_roi", (file_id, roi_id)))

    def refresh_file(self, file_id: str) -> None:
        self.calls.append(("refresh_file", file_id))


@dataclass
class FakeAcqImageList:
    """Fake list exposing a sum-intensity pool."""

    sum_intensity_analysis_pool: FakeSumIntensityPool


@dataclass
class FakeState:
    """Fake home-page state."""

    acq_image_list: FakeAcqImageList | None


@dataclass
class FakeHomeController:
    """Fake home controller exposing state."""

    state: FakeState


def _make() -> tuple[EventBus, FakeSumIntensityPool, list[SumIntensityPoolChanged]]:
    bus = EventBus()
    pool = FakeSumIntensityPool()
    home = FakeHomeController(FakeState(acq_image_list=FakeAcqImageList(pool)))
    changed: list[SumIntensityPoolChanged] = []
    bus.subscribe(SumIntensityPoolChanged, changed.append)
    controller = SumIntensityPoolController(event_bus=bus, home_controller=home)  # type: ignore[arg-type]
    controller.bind()
    return bus, pool, changed


def test_file_list_changed_rebuilds_sum_intensity_pool() -> None:
    """Loaded file-list changes should rebuild the backend pool."""
    bus, pool, changed = _make()

    bus.publish(FileListChanged(file_ids=[], rows=[]))

    assert pool.calls == [("rebuild", None)]
    assert changed[-1].change_kind is SumIntensityPoolChangeKind.REBUILD


def test_successful_sum_intensity_analysis_refreshes_rows() -> None:
    """Successful sum-intensity completion should refresh affected rows."""
    bus, pool, changed = _make()

    bus.publish(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            success=True,
        )
    )

    assert pool.calls == [("refresh_rows", ("file-a", 0, 1))]
    assert changed[-1] == SumIntensityPoolChanged(
        change_kind=SumIntensityPoolChangeKind.REFRESH_ROWS,
        file_id="file-a",
        channel=0,
        roi_id=1,
    )


def test_failed_and_non_sum_analyses_do_not_refresh_sum_intensity_pool() -> None:
    """Only successful sum-intensity changes should affect the sum pool."""
    bus, pool, changed = _make()

    bus.publish(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            success=False,
        )
    )
    bus.publish(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            success=True,
        )
    )

    assert pool.calls == []
    assert changed == []


def test_sum_intensity_analysis_changed_refreshes_rows() -> None:
    """Direct sum-intensity mutation should refresh affected rows."""
    bus, pool, changed = _make()

    bus.publish(
        AnalysisChanged(
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
        )
    )

    assert pool.calls == [("refresh_rows", ("file-a", 0, 1))]
    assert changed[-1].change_kind is SumIntensityPoolChangeKind.REFRESH_ROWS


def test_batch_file_completion_refreshes_sum_intensity_rows() -> None:
    """Successful sum-intensity batch rows should refresh affected rows."""
    bus, pool, changed = _make()

    bus.publish(
        BatchFileAnalysisCompleted(
            batch_id="batch-a",
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            file_id="file-a",
            result=BatchFileResult(
                file_path="file-a",
                analysis_name="sum_intensity",
                channel=0,
                roi_id=1,
                outcome=BatchFileOutcome.OK,
                message="ok",
            ),
        )
    )

    assert pool.calls == [("refresh_rows", ("file-a", 0, 1))]
    assert changed[-1].change_kind is SumIntensityPoolChangeKind.REFRESH_ROWS


def test_roi_delete_removes_sum_intensity_roi() -> None:
    """ROI delete should remove all sum-intensity rows for the deleted ROI."""
    bus, pool, changed = _make()

    bus.publish(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            affected_roi_id=2,
        )
    )

    assert pool.calls == [("remove_roi", ("file-a", 2))]
    assert changed[-1] == SumIntensityPoolChanged(
        change_kind=SumIntensityPoolChangeKind.REMOVE_ROI,
        file_id="file-a",
        roi_id=2,
    )


def test_roi_add_or_edit_refreshes_sum_intensity_rows() -> None:
    """ROI add/edit should seed or refresh affected sum-intensity rows."""
    bus, pool, _ = _make()

    bus.publish(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=3),
            affected_roi_id=3,
        )
    )
    bus.publish(
        RoiChanged(
            operation=RoiChangeKind.EDIT,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=3),
            affected_roi_id=3,
        )
    )

    assert pool.calls == [
        ("refresh_rows", ("file-a", 0, 3)),
        ("refresh_rows", ("file-a", 0, 3)),
    ]


def test_experiment_metadata_changed_refreshes_sum_intensity_file() -> None:
    """Experiment metadata edits should refresh all rows for the file."""
    bus, pool, changed = _make()

    bus.publish(
        MetadataChanged(
            file_id="file-a",
            metadata_section_id="experiment_metadata",
            file_list_row={"path": "file-a"},
        )
    )

    assert pool.calls == [("refresh_file", "file-a")]
    assert changed[-1] == SumIntensityPoolChanged(
        change_kind=SumIntensityPoolChangeKind.REFRESH_FILE,
        file_id="file-a",
    )


def test_image_header_metadata_changed_does_not_refresh_sum_intensity_pool() -> None:
    """Image header metadata edits should not touch the sum-intensity pool."""
    bus, pool, changed = _make()

    bus.publish(
        MetadataChanged(
            file_id="file-a",
            metadata_section_id="image_header_metadata",
            file_list_row={"path": "file-a"},
        )
    )

    assert pool.calls == []
    assert changed == []
