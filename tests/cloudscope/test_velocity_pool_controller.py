"""Tests for centralized velocity-pool runtime maintenance."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from cloudscope.controllers.velocity_pool_controller import VelocityPoolController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisChanged, AnalysisCompleted, AnalysisKind
from cloudscope.events.files import FileListChanged
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.events.velocity_pool import VelocityPoolChanged, VelocityPoolChangeKind
from cloudscope.state import PrimarySelection


@dataclass
class FakeVelocityPool:
    """Fake backend pool recording mutations."""

    calls: list[tuple[str, object]] = field(default_factory=list)
    rows: list[dict[str, object]] = field(default_factory=list)

    def rebuild(self) -> None:
        self.calls.append(("rebuild", None))

    def get_dataframe(self, *, copy: bool = True) -> pd.DataFrame:
        """Return fake pool rows for metadata refresh tests."""
        df = pd.DataFrame(self.rows)
        if copy:
            return df.copy()
        return df

    def refresh_row(self, file_id: str, *, channel: int, roi_id: int) -> None:
        self.calls.append(("refresh_row", (file_id, channel, roi_id)))

    def remove_roi(self, file_id: str, *, roi_id: int) -> None:
        self.calls.append(("remove_roi", (file_id, roi_id)))


@dataclass
class FakeAcqImageList:
    """Fake list exposing a velocity pool."""

    velocity_analysis_pool: FakeVelocityPool


@dataclass
class FakeState:
    """Fake home-page state."""

    acq_image_list: FakeAcqImageList | None


@dataclass
class FakeHomeController:
    """Fake home controller exposing state."""

    state: FakeState


def _make() -> tuple[EventBus, FakeVelocityPool, list[VelocityPoolChanged]]:
    bus = EventBus()
    pool = FakeVelocityPool()
    home = FakeHomeController(FakeState(acq_image_list=FakeAcqImageList(pool)))
    changed: list[VelocityPoolChanged] = []
    bus.subscribe(VelocityPoolChanged, changed.append)
    controller = VelocityPoolController(event_bus=bus, home_controller=home)  # type: ignore[arg-type]
    controller.bind()
    return bus, pool, changed


def test_file_list_changed_rebuilds_pool() -> None:
    """Loaded file-list changes should rebuild the backend pool."""
    bus, pool, changed = _make()

    bus.publish(FileListChanged(file_ids=[], rows=[]))

    assert pool.calls == [("rebuild", None)]
    assert changed[-1].change_kind is VelocityPoolChangeKind.REBUILD


def test_successful_velocity_analysis_refreshes_row() -> None:
    """Successful Radon velocity completion should refresh the affected row."""
    bus, pool, changed = _make()

    bus.publish(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            success=True,
        )
    )

    assert pool.calls == [("refresh_row", ("file-a", 0, 1))]
    assert changed[-1] == VelocityPoolChanged(
        change_kind=VelocityPoolChangeKind.REFRESH_ROW,
        file_id="file-a",
        channel=0,
        roi_id=1,
    )


def test_failed_analysis_and_diameter_do_not_refresh_pool() -> None:
    """Failed analyses and diameter analysis should not affect velocity pool."""
    bus, pool, changed = _make()

    bus.publish(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            success=False,
        )
    )
    bus.publish(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            success=True,
        )
    )

    assert pool.calls == []
    assert changed == []


def test_event_analysis_changed_refreshes_row() -> None:
    """Direct event CRUD mutation should refresh event columns in the pool row."""
    bus, pool, changed = _make()

    bus.publish(
        AnalysisChanged(
            analysis_kind=AnalysisKind.EVENT,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
        )
    )

    assert pool.calls == [("refresh_row", ("file-a", 0, 1))]
    assert changed[-1].change_kind is VelocityPoolChangeKind.REFRESH_ROW


def test_roi_delete_removes_affected_roi_even_after_selection_changes() -> None:
    """ROI delete should remove the deleted ROI, not the post-delete selection."""
    bus, pool, changed = _make()

    bus.publish(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1),
            affected_roi_id=2,
        )
    )

    assert pool.calls == [("remove_roi", ("file-a", 2))]
    assert changed[-1] == VelocityPoolChanged(
        change_kind=VelocityPoolChangeKind.REMOVE_ROI,
        file_id="file-a",
        roi_id=2,
    )


def test_roi_add_or_edit_refreshes_affected_row() -> None:
    """ROI add/edit should seed or refresh the affected pool row."""
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
        ("refresh_row", ("file-a", 0, 3)),
        ("refresh_row", ("file-a", 0, 3)),
    ]


def test_experiment_metadata_changed_on_empty_pool_is_noop() -> None:
    """Experiment metadata edits should no-op when the pool has no rows."""
    bus, pool, changed = _make()

    bus.publish(
        MetadataChanged(
            file_id="file-a",
            metadata_section_id="experiment_metadata",
            file_list_row={"path": "file-a"},
        )
    )

    assert pool.calls == []
    assert changed == []


def test_experiment_metadata_changed_refreshes_matching_pool_rows() -> None:
    """Experiment metadata edits should refresh each channel/roi row for the file."""
    bus = EventBus()
    pool = FakeVelocityPool()
    pool.rows = [
        {"path": "file-a", "channel": 0, "roi_id": 1},
        {"path": "file-a", "channel": 1, "roi_id": 1},
        {"path": "file-b", "channel": 0, "roi_id": 1},
    ]
    home = FakeHomeController(FakeState(acq_image_list=FakeAcqImageList(pool)))
    changed: list[VelocityPoolChanged] = []
    bus.subscribe(VelocityPoolChanged, changed.append)
    controller = VelocityPoolController(event_bus=bus, home_controller=home)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(
        MetadataChanged(
            file_id="file-a",
            metadata_section_id="experiment_metadata",
            file_list_row={"path": "file-a"},
        )
    )

    assert pool.calls == [
        ("refresh_row", ("file-a", 0, 1)),
        ("refresh_row", ("file-a", 1, 1)),
    ]
    assert len(changed) == 2
    assert all(item.change_kind is VelocityPoolChangeKind.REFRESH_ROW for item in changed)


def test_image_header_metadata_changed_does_not_refresh_pool() -> None:
    """Image header metadata edits should not touch the velocity pool."""
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
