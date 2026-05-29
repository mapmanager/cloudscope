"""Tests for AcqImageListTreeView state access and tree row updates."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from acqstore.acq_image.tree_rows import (
    ACQ_TREE_ANALYSIS_CHANNEL_FIELD,
    ACQ_TREE_ANALYSIS_NAME_FIELD,
    ACQ_TREE_ANALYSIS_ROI_ID_FIELD,
    ACQ_TREE_PATH_FIELD,
    ACQ_TREE_ROW_ID_FIELD,
    ACQ_TREE_ROW_TYPE_ANALYSIS,
    ACQ_TREE_ROW_TYPE_FIELD,
    ACQ_TREE_ROW_TYPE_FILE,
    build_analysis_tree_row_id,
)

from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import AcqImageEventsChanged
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.files import FileListChanged
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.events.selection import SelectFileIntent
from cloudscope.state import PrimarySelection
from cloudscope.views.file_list_tree_view import AcqImageListTreeView


class FakeTree:
    """Fake tree widget instance used by view tests."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.group_replacements: list[tuple[str, list[dict[str, Any]]]] = []
        self.selected: list[str] = []
        self.clear_count = 0
        self.enabled: bool | None = None
        self.displayed_rows: list[dict[str, Any]] = []

    def set_data(self, rows: list[dict[str, Any]]) -> None:
        self.rows = [dict(r) for r in rows]

    def replace_group_rows(self, group_id: str, rows: list[dict[str, Any]]) -> None:
        self.group_replacements.append((group_id, [dict(r) for r in rows]))

    def clear_selection(self) -> None:
        self.clear_count += 1
        self.selected = []

    def set_selected_row_ids(self, row_ids: list[str], *, origin: str) -> None:
        self.selected = list(row_ids)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def get_selected_rows(self) -> list[dict[str, Any]]:
        return []

    async def get_displayed_rows(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.displayed_rows]


def _file_row(file_id: str, *, name: str | None = None, dirty: bool = False) -> dict[str, Any]:
    return {
        ACQ_TREE_ROW_ID_FIELD: file_id,
        ACQ_TREE_PATH_FIELD: [file_id],
        ACQ_TREE_ROW_TYPE_FIELD: ACQ_TREE_ROW_TYPE_FILE,
        ACQ_TREE_ANALYSIS_NAME_FIELD: None,
        ACQ_TREE_ANALYSIS_CHANNEL_FIELD: None,
        ACQ_TREE_ANALYSIS_ROI_ID_FIELD: None,
        "name": name or file_id,
        "dirty": dirty,
    }


def _analysis_row(file_id: str, analysis_name: str, channel: int, roi_id: int) -> dict[str, Any]:
    row_id = build_analysis_tree_row_id(file_id, analysis_name, channel, roi_id)
    return {
        ACQ_TREE_ROW_ID_FIELD: row_id,
        ACQ_TREE_PATH_FIELD: [file_id, row_id],
        ACQ_TREE_ROW_TYPE_FIELD: ACQ_TREE_ROW_TYPE_ANALYSIS,
        ACQ_TREE_ANALYSIS_NAME_FIELD: analysis_name,
        ACQ_TREE_ANALYSIS_CHANNEL_FIELD: channel,
        ACQ_TREE_ANALYSIS_ROI_ID_FIELD: roi_id,
        # Display-overloaded schema fields populated by AcqStore for
        # analysis rows (see acqstore.acq_image._build_analysis_tree_rows).
        "name": analysis_name,
        "num_channels": channel,
        "num_rois": roi_id,
    }


class FakeAcqImage:
    """Fake AcqImage exposing the tree-row API."""

    def __init__(self, file_id: str, *, dirty: bool = False, analyses: list[dict[str, Any]] | None = None) -> None:
        self.file_id = file_id
        self.dirty = dirty
        self._analyses = list(analyses or [])

    def get_tree_rows(self) -> list[dict[str, Any]]:
        return [_file_row(self.file_id, dirty=self.dirty), *self._analyses]


class FakeAcqImageList:
    """Fake AcqImageList exposing the tree-row API."""

    def __init__(self, images: list[FakeAcqImage]) -> None:
        self._images = {image.file_id: image for image in images}

    def get_file_by_id(self, file_id: str) -> FakeAcqImage | None:
        return self._images.get(file_id)

    def get_tree_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for image in self._images.values():
            rows.extend(image.get_tree_rows())
        return rows


@dataclass
class FakeState:
    acq_image_list: FakeAcqImageList | None = None
    selection: PrimarySelection = field(default_factory=PrimarySelection)


def _make_view(state: FakeState | None = None) -> AcqImageListTreeView:
    view = AcqImageListTreeView(event_bus=EventBus(), app_state=state, table_font_size_px=13)
    view._tree = FakeTree()  # type: ignore[assignment]
    return view


def test_refresh_from_state_reads_tree_rows_from_app_state() -> None:
    image = FakeAcqImage(
        "/tmp/a.oir",
        analyses=[_analysis_row("/tmp/a.oir", "radon_velocity", 0, 1)],
    )
    state = FakeState(
        acq_image_list=FakeAcqImageList([image]),
        selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
    )
    view = _make_view(state)
    view.current_selection = state.selection

    view.refresh_from_state()

    assert view._tree is not None
    assert len(view._tree.rows) == 2
    assert view._tree.rows[0][ACQ_TREE_ROW_ID_FIELD] == "/tmp/a.oir"
    assert view._tree.rows[1][ACQ_TREE_ROW_TYPE_FIELD] == ACQ_TREE_ROW_TYPE_ANALYSIS
    assert view._tree.rows[1]["name"] == "radon_velocity"
    assert view._tree.selected == ["/tmp/a.oir"]


def test_file_list_changed_rebuilds_from_app_state_not_event_rows() -> None:
    image = FakeAcqImage("/tmp/b.oir")
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id="/tmp/b.oir", channel=0, roi_id=1)

    view._on_file_list_changed(
        FileListChanged(file_ids=["/tmp/b.oir"], rows=[{"path": "/tmp/b.oir", "name": "ignored"}])
    )

    assert view._tree is not None
    assert [r[ACQ_TREE_ROW_ID_FIELD] for r in view._tree.rows] == ["/tmp/b.oir"]
    assert view._tree.selected == ["/tmp/b.oir"]


def test_metadata_changed_replaces_one_subtree_from_app_state() -> None:
    image = FakeAcqImage(
        "/tmp/a.oir",
        dirty=True,
        analyses=[_analysis_row("/tmp/a.oir", "diameter", 1, 2)],
    )
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)

    view._on_metadata_changed(
        MetadataChanged(
            file_id="/tmp/a.oir",
            metadata_section_id="header",
            file_list_row={"path": "/tmp/a.oir", "ignored": True},
        )
    )

    assert view._tree is not None
    assert len(view._tree.group_replacements) == 1
    group_id, rows = view._tree.group_replacements[0]
    assert group_id == "/tmp/a.oir"
    assert rows[0]["dirty"] is True
    assert rows[1]["name"] == "diameter"


def test_analysis_completed_replaces_subtree_from_app_state() -> None:
    image = FakeAcqImage("/tmp/a.oir", dirty=True)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
            success=True,
        )
    )

    assert view._tree is not None
    assert [r[0] for r in view._tree.group_replacements] == ["/tmp/a.oir"]


def test_analysis_completed_refreshes_even_when_success_is_false() -> None:
    """Per-file AnalysisCompleted with success=False (e.g. a sibling file
    failed in a batch) must still refresh the subtree, because the
    underlying AcqImage is the authoritative source of truth."""
    image = FakeAcqImage("/tmp/a.oir", dirty=True)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
            success=False,
        )
    )

    assert view._tree is not None
    assert [r[0] for r in view._tree.group_replacements] == ["/tmp/a.oir"]


def test_replace_group_rows_re_syncs_selection_for_same_file() -> None:
    """After replacing a file's subtree, the tree's selection must be
    re-applied because AG Grid transactions drop selection on replaced
    rows."""
    image = FakeAcqImage(
        "/tmp/a.oir",
        analyses=[_analysis_row("/tmp/a.oir", "radon_velocity", 2, 7)],
    )
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(
        file_id="/tmp/a.oir",
        channel=2,
        roi_id=7,
        analysis_name="radon_velocity",
    )

    view._replace_group_rows_from_acq_image("/tmp/a.oir")

    expected = build_analysis_tree_row_id("/tmp/a.oir", "radon_velocity", 2, 7)
    assert view._tree is not None
    assert view._tree.selected == [expected]


def test_replace_group_rows_does_not_re_sync_for_different_file() -> None:
    """Refreshing one file's subtree must not touch the tree selection
    when the current selection points at a different file."""
    image_a = FakeAcqImage("/tmp/a.oir")
    image_b = FakeAcqImage("/tmp/b.oir", dirty=True)
    state = FakeState(acq_image_list=FakeAcqImageList([image_a, image_b]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1)

    assert view._tree is not None
    pre_selected = list(view._tree.selected)

    view._replace_group_rows_from_acq_image("/tmp/b.oir")

    assert view._tree.selected == pre_selected


def test_roi_changed_replaces_subtree_from_app_state() -> None:
    image = FakeAcqImage("/tmp/a.oir", dirty=True)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
        )
    )

    assert view._tree is not None
    assert [r[0] for r in view._tree.group_replacements] == ["/tmp/a.oir"]


def test_acq_image_events_changed_replaces_subtree_from_app_state() -> None:
    image = FakeAcqImage("/tmp/a.oir", dirty=True)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)

    view._on_acq_image_events_changed(
        AcqImageEventsChanged(
            selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
        )
    )

    assert view._tree is not None
    assert [r[0] for r in view._tree.group_replacements] == ["/tmp/a.oir"]


def test_on_row_selected_publishes_simple_intent_for_file_row() -> None:
    state = FakeState()
    view = _make_view(state)
    published: list[SelectFileIntent] = []
    view.event_bus.subscribe(SelectFileIntent, published.append)

    view._on_row_selected(_file_row("/tmp/a.oir"))

    assert len(published) == 1
    assert published[0].file_id == "/tmp/a.oir"
    assert published[0].channel is None
    assert published[0].roi_id is None
    assert published[0].analysis_name is None


def test_on_row_selected_publishes_full_intent_for_analysis_row() -> None:
    state = FakeState()
    view = _make_view(state)
    published: list[SelectFileIntent] = []
    view.event_bus.subscribe(SelectFileIntent, published.append)

    view._on_row_selected(_analysis_row("/tmp/a.oir", "radon_velocity", 2, 7))

    assert len(published) == 1
    assert published[0].file_id == "/tmp/a.oir"
    assert published[0].channel == 2
    assert published[0].roi_id == 7
    assert published[0].analysis_name == "radon_velocity"


def test_sync_table_selection_selects_file_row_when_no_analysis_name() -> None:
    state = FakeState()
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1)

    view._sync_table_selection()

    assert view._tree is not None
    assert view._tree.selected == ["/tmp/a.oir"]


def test_sync_table_selection_selects_analysis_row_when_analysis_name_set() -> None:
    state = FakeState()
    view = _make_view(state)
    view.current_selection = PrimarySelection(
        file_id="/tmp/a.oir",
        channel=2,
        roi_id=7,
        analysis_name="radon_velocity",
    )

    view._sync_table_selection()

    expected = build_analysis_tree_row_id("/tmp/a.oir", "radon_velocity", 2, 7)
    assert view._tree is not None
    assert view._tree.selected == [expected]


def test_sync_table_selection_clears_when_no_file_id() -> None:
    state = FakeState()
    view = _make_view(state)
    view.current_selection = PrimarySelection()

    view._sync_table_selection()

    assert view._tree is not None
    assert view._tree.clear_count == 1
    assert view._tree.selected == []


def test_get_displayed_file_ids_filters_to_file_rows_only() -> None:
    state = FakeState()
    view = _make_view(state)
    assert isinstance(view._tree, FakeTree)
    view._tree.displayed_rows = [
        _file_row("/tmp/b.oir"),
        _analysis_row("/tmp/b.oir", "radon_velocity", 0, 1),
        _file_row("/tmp/a.oir"),
    ]

    file_ids = asyncio.run(view.get_displayed_file_ids())

    assert file_ids == ["/tmp/b.oir", "/tmp/a.oir"]


def test_forwards_enabled_state_to_tree() -> None:
    state = FakeState()
    view = _make_view(state)

    view.on_enabled_changed(False)

    assert view._tree is not None
    assert view._tree.enabled is False
