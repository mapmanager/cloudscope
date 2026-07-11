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
from cloudscope.events.files import FileListChanged, ImageDataLoaded
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.events.selection import (
    SELECTION_SOURCE_CHANNEL,
    SELECTION_SOURCE_FILE_LIST_TREE,
    SELECTION_SOURCE_VELOCITY_POOL,
    SelectFileIntent,
)
from cloudscope.state import PrimarySelection
from cloudscope.views.file_list_tree_view import AcqImageListTreeView


class FakeTree:
    """Fake tree widget instance used by view tests."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.group_replacements: list[tuple[str, list[dict[str, Any]]]] = []
        self.row_updates: list[tuple[str, dict[str, Any]]] = []
        self.selected: list[str] = []
        self.clear_count = 0
        self.enabled: bool | None = None
        self.displayed_rows: list[dict[str, Any]] = []
        self.scroll_calls: list[str] = []

    def set_data(self, rows: list[dict[str, Any]]) -> None:
        self.rows = [dict(r) for r in rows]

    def replace_group_rows(self, group_id: str, rows: list[dict[str, Any]]) -> None:
        self.group_replacements.append((group_id, [dict(r) for r in rows]))

    def update_row(self, row_id: str, row: dict[str, Any]) -> None:
        self.row_updates.append((row_id, dict(row)))

    def clear_selection(self) -> None:
        self.clear_count += 1
        self.selected = []

    def set_selected_row_ids(self, row_ids: list[str], *, origin: str) -> None:
        self.selected = list(row_ids)

    def scroll_row_id_into_view(self, row_id: str) -> None:
        self.scroll_calls.append(row_id)

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

    def __init__(
        self,
        file_id: str,
        *,
        dirty: bool = False,
        analyses: list[dict[str, Any]] | None = None,
        fully_loaded: bool = False,
        loaded_marker: str = '',
    ) -> None:
        self.file_id = file_id
        self.dirty = dirty
        self._analyses = list(analyses or [])
        self._fully_loaded = bool(fully_loaded)
        self._loaded_marker = str(loaded_marker)

    @property
    def is_fully_loaded(self) -> bool:
        """Return whether lazy image/analysis data are loaded."""
        return self._fully_loaded

    @property
    def images_loaded(self) -> bool:
        """Return whether primary image pixels are loaded."""
        return self._fully_loaded

    def get_tree_rows(self) -> list[dict[str, Any]]:
        file_row = _file_row(self.file_id, dirty=self.dirty)
        if self._loaded_marker:
            file_row['loaded'] = self._loaded_marker
        return [file_row, *self._analyses]


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
    file_ids: list[str] = field(default_factory=list)


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


def test_refresh_from_state_masks_file_rows_when_blinded() -> None:
    image = FakeAcqImage("/tmp/a.oir")
    state = FakeState(
        acq_image_list=FakeAcqImageList([image]),
        file_ids=["/tmp/a.oir"],
        selection=PrimarySelection(file_id="/tmp/a.oir", channel=0, roi_id=1),
    )
    view = _make_view(state)
    view.set_blinded_provider(lambda: True)
    view.current_selection = state.selection

    view.refresh_from_state()

    assert view._tree is not None
    assert view._tree.rows[0][ACQ_TREE_ROW_ID_FIELD] == "/tmp/a.oir"
    assert view._tree.rows[0]["name"] == "File 1"


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


def test_replace_group_rows_refreshes_data_without_touching_selection() -> None:
    """Refreshing a file's subtree must NOT re-apply selection.

    AG Grid's id-keyed ``applyTransaction`` preserves selection for surviving
    rows (verified in-browser), so re-selecting here is unnecessary and caused
    a visible deselect/reselect flash on user clicks. The refresh replaces the
    group's row data and leaves selection to the selection path.
    """
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

    assert view._tree is not None
    assert [r[0] for r in view._tree.group_replacements] == ["/tmp/a.oir"]
    # Selection is not churned by a data refresh.
    assert view._tree.selected == []


def test_replace_group_rows_does_not_touch_selection_for_different_file() -> None:
    """Refreshing one file's subtree must not touch the tree selection."""
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
    assert published[0].source == SELECTION_SOURCE_FILE_LIST_TREE


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
    assert published[0].source == SELECTION_SOURCE_FILE_LIST_TREE


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


def test_on_primary_selection_changed_does_not_refresh_loaded_rows() -> None:
    """Selection changes update selection only, even when data are loaded."""
    image = FakeAcqImage('/tmp/a.oir', fully_loaded=True, loaded_marker='✅')
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=0, roi_id=1)

    view.on_primary_selection_changed()

    assert view._tree is not None
    assert view._tree.group_replacements == []
    assert view._tree.selected == ['/tmp/a.oir']


def test_image_data_loaded_refreshes_file_subtree() -> None:
    """ImageDataLoaded refreshes row data without changing selection."""
    image = FakeAcqImage('/tmp/a.oir', fully_loaded=True, loaded_marker='✅')
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=0, roi_id=1)

    view._on_image_data_loaded(
        ImageDataLoaded(file_id='/tmp/a.oir', file_list_row={'path': '/tmp/a.oir'})
    )

    assert view._tree is not None
    assert len(view._tree.group_replacements) == 1
    group_id, rows = view._tree.group_replacements[0]
    assert group_id == '/tmp/a.oir'
    assert rows[0]['loaded'] == '✅'
    assert view._tree.selected == []


def test_on_primary_selection_changed_syncs_when_images_not_loaded() -> None:
    image = FakeAcqImage('/tmp/a.oir', fully_loaded=False)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=0, roi_id=1)

    view.on_primary_selection_changed()

    assert view._tree is not None
    assert view._tree.group_replacements == []
    assert view._tree.selected == ['/tmp/a.oir']


def test_scroll_into_view_on_external_source_selects_file_row() -> None:
    """A programmatic selection from an external source (e.g. pool plot)
    scrolls the selected file row into view."""
    image = FakeAcqImage('/tmp/a.oir', fully_loaded=False)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=0, roi_id=1)
    view.current_selection_source = SELECTION_SOURCE_VELOCITY_POOL

    view.on_primary_selection_changed()

    assert view._tree is not None
    assert view._tree.scroll_calls == ['/tmp/a.oir']


def test_scroll_into_view_on_external_source_targets_analysis_row() -> None:
    """External selection of an analysis scrolls that analysis child row."""
    image = FakeAcqImage(
        '/tmp/a.oir',
        fully_loaded=False,
        analyses=[_analysis_row('/tmp/a.oir', 'radon_velocity', 2, 7)],
    )
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(
        file_id='/tmp/a.oir',
        channel=2,
        roi_id=7,
        analysis_name='radon_velocity',
    )
    view.current_selection_source = SELECTION_SOURCE_VELOCITY_POOL

    view.on_primary_selection_changed()

    expected = build_analysis_tree_row_id('/tmp/a.oir', 'radon_velocity', 2, 7)
    assert view._tree is not None
    assert view._tree.scroll_calls == [expected]


def test_no_scroll_on_tree_click_source() -> None:
    """A selection echoed from a user's own tree click must NOT scroll."""
    image = FakeAcqImage('/tmp/a.oir', fully_loaded=False)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=0, roi_id=1)
    view.current_selection_source = SELECTION_SOURCE_FILE_LIST_TREE

    view.on_primary_selection_changed()

    assert view._tree is not None
    assert view._tree.scroll_calls == []


def test_no_scroll_on_channel_source() -> None:
    """A channel-only change must NOT scroll the tree."""
    image = FakeAcqImage('/tmp/a.oir', fully_loaded=False)
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=0, roi_id=1)
    view.current_selection_source = SELECTION_SOURCE_CHANNEL

    view.on_primary_selection_changed()

    assert view._tree is not None
    assert view._tree.scroll_calls == []


def test_scroll_into_view_when_images_loaded_external_source() -> None:
    """The scroll fires in the images-loaded branch too (external source)."""
    image = FakeAcqImage('/tmp/a.oir', fully_loaded=True, loaded_marker='✅')
    state = FakeState(acq_image_list=FakeAcqImageList([image]))
    view = _make_view(state)
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=0, roi_id=1)
    view.current_selection_source = SELECTION_SOURCE_VELOCITY_POOL

    view.on_primary_selection_changed()

    assert view._tree is not None
    assert view._tree.group_replacements == []
    assert view._tree.scroll_calls == ['/tmp/a.oir']


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


def test_build_passes_sized_parent_to_tree_widget(monkeypatch) -> None:
    """Tree build should use a flex fill container, not TreeWidget's 24rem default."""
    from unittest.mock import MagicMock

    import cloudscope.views.file_list_tree_view as tree_view_mod

    captured: dict[str, object] = {}
    mock_root = MagicMock()

    class CapturingTreeWidget:
        def __init__(self, **kwargs: object) -> None:
            pass

        def build(self, parent: object | None = None) -> MagicMock:
            captured['parent'] = parent
            return MagicMock()

    mock_column = MagicMock()
    mock_with_classes = MagicMock()
    mock_with_classes.__enter__ = MagicMock(return_value=mock_root)
    mock_with_classes.__exit__ = MagicMock(return_value=False)
    mock_column.classes.return_value = mock_with_classes

    monkeypatch.setattr(tree_view_mod, 'TreeWidget', CapturingTreeWidget)
    monkeypatch.setattr(tree_view_mod, 'schema_to_column_defs', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(tree_view_mod.ui, 'column', lambda: mock_column)

    view = AcqImageListTreeView(
        event_bus=EventBus(),
        table_font_size_px=13,
        initially_visible=False,
    )
    built_root = view.build()

    assert captured['parent'] is mock_root
    assert built_root is mock_root
    mock_column.classes.assert_called_once_with(tree_view_mod._FILE_TREE_ROOT_CLASSES)


def test_build_schema_column_defs_respects_default_visible_columns() -> None:
    """default_visible_columns should hide schema fields outside the allowlist."""
    view = AcqImageListTreeView(
        event_bus=EventBus(),
        default_visible_columns=frozenset({'name', 'parent', 'grandparent', 'dims'}),
    )
    columns = view._build_schema_column_defs(13)
    by_field = {col.field: col for col in columns}

    assert by_field['name'].hide is False
    assert by_field['parent'].hide is False
    assert by_field['grandparent'].hide is False
    assert by_field['dims'].hide is False
    assert by_field['saved'].hide is True
    assert by_field['loaded'].hide is True
    assert by_field['num_channels'].hide is True


def test_build_schema_column_defs_without_profile_uses_schema_defaults() -> None:
    """When default_visible_columns is None, schema visibility is unchanged."""
    view = AcqImageListTreeView(event_bus=EventBus())
    columns = view._build_schema_column_defs(13)
    by_field = {col.field: col for col in columns}

    assert by_field['name'].hide is False
    assert by_field['path'].hide is True
    assert by_field['condition'].hide is True


def test_left_panel_file_list_view_uses_toolbar_view_id() -> None:
    """Left toolbar file list should register under LEFT_TOOLBAR_FILE_LIST."""
    from cloudscope.views.left_panel_file_list_view import LeftPanelFileListView
    from cloudscope.views.view_ids import ViewId

    view = LeftPanelFileListView(event_bus=EventBus())
    assert view.view_id is ViewId.LEFT_TOOLBAR_FILE_LIST


def test_save_as_tif_publishes_intent_for_selected_file(monkeypatch: Any) -> None:
    """Save As Tif... should publish SaveAsTifIntent for the selected file row."""
    from cloudscope.events.files import SaveAsTifIntent
    from cloudscope.views import file_list_tree_view as tree_view_mod

    published: list[object] = []

    class _Bus:
        def publish(self, event: object) -> None:
            published.append(event)

    class _Tree:
        def get_selected_rows(self) -> list[dict[str, Any]]:
            return [_file_row('/tmp/a.tif')]

    view = object.__new__(tree_view_mod.AcqImageListTreeView)
    view.event_bus = _Bus()
    view._tree = _Tree()

    view._save_selected_file_as_tif()

    assert len(published) == 1
    assert isinstance(published[0], SaveAsTifIntent)
    assert published[0].file_id == '/tmp/a.tif'


def test_save_as_tif_no_selection_notifies(monkeypatch: Any) -> None:
    """Save As Tif... should warn when no tree row is selected."""
    from cloudscope.views import file_list_tree_view as tree_view_mod

    notified: list[tuple[str, str]] = []
    monkeypatch.setattr(
        tree_view_mod.ui,
        'notify',
        lambda message, type='info': notified.append((message, type)),
    )

    class _Tree:
        def get_selected_rows(self) -> list[dict[str, Any]]:
            return []

    view = object.__new__(tree_view_mod.AcqImageListTreeView)
    view.event_bus = EventBus()
    view._tree = _Tree()

    view._save_selected_file_as_tif()

    assert notified == [('No file selected', 'warning')]
