"""Tests for AcqImageListTableView state access and row updates."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import AcqImageEventsChanged
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.files import FileListChanged
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.state import PrimarySelection
from cloudscope.views.file_list_view import AcqImageListTableView


class FakeTable:
    """Fake table widget instance used by view tests."""

    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []
        self.updated_rows: list[tuple[str, dict[str, object]]] = []
        self.selected: list[str] = []
        self.clear_count = 0
        self.enabled: bool | None = None
        self.displayed_rows: list[dict[str, object]] = []

    def set_data(self, rows: list[dict[str, object]]) -> None:
        """Record replacement rows."""
        self.rows = list(rows)

    def update_row(self, row_id: str, row: dict[str, object]) -> None:
        """Record row update."""
        self.updated_rows.append((row_id, dict(row)))

    def clear_selection(self) -> None:
        """Record selection clearing."""
        self.clear_count += 1
        self.selected = []

    def set_selected_row_ids(self, row_ids: list[str], *, origin: str) -> None:
        """Record selected row ids."""
        self.selected = list(row_ids)

    def set_enabled(self, enabled: bool) -> None:
        """Record enabled state."""
        self.enabled = bool(enabled)

    async def get_displayed_rows(self) -> list[dict[str, object]]:
        """Return fake browser-displayed rows."""
        return list(self.displayed_rows)


class FakeAcqImage:
    """Fake AcqImage with schema row API."""

    def __init__(self, file_id: str, *, dirty: bool = False) -> None:
        self.file_id = file_id
        self.dirty = dirty

    def get_schema_row(self) -> dict[str, object]:
        """Return fake table row."""
        return {"path": self.file_id, "dirty": self.dirty}


class FakeAcqImageList:
    """Fake AcqImageList with lookup and row APIs."""

    def __init__(self, images: list[FakeAcqImage]) -> None:
        self._images = {image.file_id: image for image in images}

    def get_file_by_id(self, file_id: str) -> FakeAcqImage | None:
        """Return fake image by id."""
        return self._images.get(file_id)

    def get_schema_rows(self) -> list[dict[str, object]]:
        """Return fake table rows."""
        return [image.get_schema_row() for image in self._images.values()]


@dataclass
class FakeState:
    """Fake app state holding list and selection."""

    acq_image_list: FakeAcqImageList | None = None
    selection: PrimarySelection = field(default_factory=PrimarySelection)


def _make_view(state: FakeState) -> AcqImageListTableView:
    """Create a file-list view with fake table already attached."""
    view = AcqImageListTableView(event_bus=EventBus(), app_state=state, table_font_size_px=13)
    view._table = FakeTable()  # type: ignore[assignment]
    return view


def test_file_list_view_has_no_public_set_data() -> None:
    """The view should not expose a second data source API."""
    view = AcqImageListTableView(event_bus=EventBus(), table_font_size_px=13)

    assert not hasattr(view, "set_data")


def test_refresh_from_state_uses_app_state_acq_image_list() -> None:
    """Refresh should read rows from app_state.acq_image_list."""
    state = FakeState(
        acq_image_list=FakeAcqImageList([FakeAcqImage("/tmp/a.oir")]),
        selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
    )
    view = _make_view(state)
    view.current_selection = state.selection

    view.refresh_from_state()

    assert view._table is not None
    assert view._table.rows == [{"path": "/tmp/a.oir", "dirty": False}]
    assert view._table.selected == ["/tmp/a.oir"]


def test_file_list_changed_replaces_rows_without_backend_cache() -> None:
    """FileListChanged should use event rows and not require a local list."""
    state = FakeState()
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id="/tmp/b.oir", channel=0, roi_id=1)

    view._on_file_list_changed(FileListChanged(file_ids=["/tmp/b.oir"], rows=[{"path": "/tmp/b.oir"}]))

    assert view._table is not None
    assert view._table.rows == [{"path": "/tmp/b.oir"}]
    assert view._table.selected == ["/tmp/b.oir"]


def test_analysis_completed_updates_one_row_from_app_state() -> None:
    """AnalysisCompleted should patch one row from AcqImage.get_schema_row()."""
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

    assert view._table is not None
    assert view._table.updated_rows == [("/tmp/a.oir", {"path": "/tmp/a.oir", "dirty": True})]


def test_roi_changed_updates_one_row_from_app_state() -> None:
    """RoiChanged should patch one row from AcqImage.get_schema_row()."""
    image = FakeAcqImage("/tmp/a.oir", dirty=True)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
        )
    )

    assert view._table is not None
    assert view._table.updated_rows == [("/tmp/a.oir", {"path": "/tmp/a.oir", "dirty": True})]


def test_file_list_view_forwards_enabled_state_to_table() -> None:
    """File-list view should explicitly disable its table widget."""
    state = FakeState()
    view = _make_view(state)

    view.on_enabled_changed(False)

    assert view._table is not None
    assert view._table.enabled is False


def test_acq_image_events_changed_updates_one_row_from_app_state() -> None:
    """AcqImageEventsChanged should patch one row from AcqImage.get_schema_row()."""
    image = FakeAcqImage("/tmp/a.oir", dirty=True)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)

    view._on_acq_image_events_changed(
        AcqImageEventsChanged(
            selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
        )
    )

    assert view._table is not None
    assert view._table.updated_rows == [("/tmp/a.oir", {"path": "/tmp/a.oir", "dirty": True})]


def test_get_displayed_file_ids_uses_visible_filtered_sorted_rows() -> None:
    """Visible file ids should come from TableWidget displayed rows."""
    state = FakeState()
    view = _make_view(state)
    assert isinstance(view._table, FakeTable)
    view._table.displayed_rows = [
        {"path": "/tmp/b.oir"},
        {"path": "/tmp/a.oir"},
        {"path": None},
    ]

    file_ids = asyncio.run(view.get_displayed_file_ids())

    assert file_ids == ["/tmp/b.oir", "/tmp/a.oir"]