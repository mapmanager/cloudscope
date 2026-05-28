"""Smoke tests for ``nicewidgets.tree_widget`` (no live NiceGUI client)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from nicewidgets.aggrid_common.column_def import ColumnDef
from nicewidgets.tree_widget.config import TreeWidgetConfig, scaled_row_header_heights_px
from nicewidgets.tree_widget.tree_widget import (
    TreeWidget,
    _auto_inject_show_row_group,
    _get_row_id_js_expression,
    validate_row_id_field,
    validate_rows_for_row_id_field,
)
from nicewidgets.tree_widget import tree_widget


def _sample_rows() -> list[dict[str, Any]]:
    return [
        {'row_id': '/a', 'hierarchy_path': ['/a'], 'name': 'A'},
        {'row_id': '/a::1', 'hierarchy_path': ['/a', '/a::1'], 'name': 'A1'},
        {'row_id': '/b', 'hierarchy_path': ['/b'], 'name': 'B'},
    ]


def _sample_columns() -> list[ColumnDef]:
    return [
        ColumnDef(field='row_id', headerName='Row Id', hide=True),
        ColumnDef(field='name', headerName='Name'),
    ]


def test_validate_row_id_field_rejects_empty() -> None:
    with pytest.raises(ValueError, match='row_id_field'):
        validate_row_id_field('')
    with pytest.raises(ValueError, match='row_id_field'):
        validate_row_id_field('   ')


def test_validate_rows_missing_key() -> None:
    with pytest.raises(ValueError, match='missing'):
        validate_rows_for_row_id_field([{'a': 1}], 'id')


def test_validate_rows_non_str_id() -> None:
    with pytest.raises(ValueError, match='str'):
        validate_rows_for_row_id_field([{'id': 1}], 'id')


def test_validate_rows_duplicate_ids() -> None:
    with pytest.raises(ValueError, match='Duplicate'):
        validate_rows_for_row_id_field([{'id': 'x'}, {'id': 'x'}], 'id')


def test_tree_widget_config_defaults() -> None:
    cfg = TreeWidgetConfig()
    assert cfg.selection_mode == 'single'
    assert cfg.clear_selection_on_set_data is True
    assert cfg.enable_keyboard_row_nav is True
    assert cfg.auto_size_columns is True


def test_scaled_row_header_heights_px_clamped() -> None:
    r, h = scaled_row_header_heights_px(13)
    assert r == 38 and h == 37


def test_get_row_id_js_expression_escapes_field_name() -> None:
    js = _get_row_id_js_expression('path')
    assert 'params.data' in js
    assert '"path"' in js


def test_build_aggrid_options_tree_defaults() -> None:
    tw = TreeWidget(
        columns=_sample_columns(),
        row_id_field='row_id',
        rows=_sample_rows(),
    )
    opts = tw._build_aggrid_options()
    assert opts['treeData'] is True
    assert ':getDataPath' in opts
    assert ':getRowId' in opts
    # AG Grid v34: `groupDisplayType: 'custom'` is the documented option
    # for both row grouping and tree data; `treeDataDisplayType` does NOT
    # accept 'custom' as a value and would be silently ignored.
    assert opts['groupDisplayType'] == 'custom'
    assert 'treeDataDisplayType' not in opts
    assert 'autoGroupColumnDef' not in opts
    # AG Grid Enterprise default context menu (Copy / Copy with Headers /
    # Export / ...) must be suppressed so the NiceGUI ui.context_menu owned
    # by the widget is the only menu the user sees. Browser default menu
    # over the grid surface is also prevented.
    assert opts['suppressContextMenu'] is True
    assert opts['preventDefaultOnContextMenu'] is True


def test_auto_inject_show_row_group_sets_flag_on_aggroupcellrenderer_column() -> None:
    """The column with cellRenderer agGroupCellRenderer gets showRowGroup=True."""
    cols = [
        {'field': 'a', 'headerName': 'A'},
        {'field': 'name', 'headerName': 'Name', 'cellRenderer': 'agGroupCellRenderer'},
        {'field': 'b', 'headerName': 'B'},
    ]
    _auto_inject_show_row_group(cols)
    assert cols[0].get('showRowGroup') is None
    assert cols[1]['showRowGroup'] is True
    assert cols[2].get('showRowGroup') is None


def test_auto_inject_show_row_group_is_idempotent() -> None:
    """If caller already set showRowGroup, do not overwrite."""
    cols = [
        {
            'field': 'name',
            'headerName': 'Name',
            'cellRenderer': 'agGroupCellRenderer',
            'showRowGroup': 'name',
        },
    ]
    _auto_inject_show_row_group(cols)
    assert cols[0]['showRowGroup'] == 'name'


def test_auto_inject_show_row_group_no_op_when_no_aggroupcellrenderer() -> None:
    """Callers without an agGroupCellRenderer column are untouched."""
    cols = [{'field': 'a', 'headerName': 'A'}]
    _auto_inject_show_row_group(cols)
    assert 'showRowGroup' not in cols[0]


def test_treewidget_init_auto_injects_show_row_group_on_group_renderer_column() -> None:
    """End-to-end: TreeWidget __init__ injects showRowGroup when needed."""
    cols = [
        ColumnDef(field='row_id', headerName='Row Id', hide=True),
        ColumnDef(
            field='name',
            headerName='Name',
            extra={'cellRenderer': 'agGroupCellRenderer'},
        ),
    ]
    tw = TreeWidget(columns=cols, row_id_field='row_id', rows=_sample_rows())
    name_col = next(c for c in tw._column_defs if c['field'] == 'name')
    assert name_col['showRowGroup'] is True


def test_treewidget_skips_show_row_group_inject_when_auto_group_column_def_set() -> None:
    """Caller-supplied autoGroupColumnDef path does not need showRowGroup injection."""
    cols = [
        ColumnDef(field='row_id', headerName='Row Id', hide=True),
        ColumnDef(
            field='name',
            headerName='Name',
            extra={'cellRenderer': 'agGroupCellRenderer'},
        ),
    ]
    tw = TreeWidget(
        columns=cols,
        row_id_field='row_id',
        rows=_sample_rows(),
        auto_group_column_def={'headerName': 'Group'},
    )
    name_col = next(c for c in tw._column_defs if c['field'] == 'name')
    assert 'showRowGroup' not in name_col


def test_build_browser_copy_script_includes_displayed_rows_and_clipboard() -> None:
    """Browser-mode copy must do row read + clipboard write in one JS call."""
    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())
    tw._grid = SimpleNamespace(id=99)

    script = tw._build_browser_copy_script()

    assert 'getElement(99)' in script
    assert 'forEachNodeAfterFilterAndSort' in script
    assert 'navigator.clipboard.writeText' in script
    # Legacy fallback for non-secure contexts / older browsers.
    assert "execCommand('copy')" in script
    # Headers reflect visible columns only (row_id is hidden in sample).
    assert '"Name"' in script
    assert '"Row Id"' not in script


def test_copy_table_data_uses_pyperclip_in_native_window(monkeypatch: Any) -> None:
    """Native window path should bypass JS and use pyperclip on python rows."""
    import asyncio

    copied: list[str] = []
    monkeypatch.setattr(tree_widget, 'app', SimpleNamespace(native=SimpleNamespace(main_window=object())))
    monkeypatch.setattr(tree_widget, 'pyperclip', SimpleNamespace(copy=copied.append))
    monkeypatch.setattr(tree_widget.ui, 'notify', lambda *_a, **_k: None)

    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())

    asyncio.run(tw._copy_table_data_to_clipboard())

    assert copied  # exact TSV shape covered by browser-script test
    assert 'Name' in copied[0]


def test_copy_table_data_runs_browser_script_and_notifies_on_success(monkeypatch: Any) -> None:
    """Browser path should run the single-roundtrip JS and notify on ok=True."""
    import asyncio

    scripts: list[str] = []
    notifications: list[tuple[str, str]] = []

    async def fake_run_javascript(script: str, timeout: float = 1.0) -> dict[str, Any]:
        scripts.append(script)
        assert timeout == 5.0
        return {'ok': True}

    monkeypatch.setattr(tree_widget, 'app', SimpleNamespace(native=None))
    monkeypatch.setattr(tree_widget.ui, 'run_javascript', fake_run_javascript)
    monkeypatch.setattr(
        tree_widget.ui,
        'notify',
        lambda message, type='info': notifications.append((message, type)),
    )

    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())
    tw._grid = SimpleNamespace(id=99)

    asyncio.run(tw._copy_table_data_to_clipboard())

    assert len(scripts) == 1
    assert 'navigator.clipboard.writeText' in scripts[0]
    assert notifications == [('Tree data copied to clipboard', 'positive')]


def test_set_data_clears_selection_by_default() -> None:
    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())
    tw.set_selected_row_ids(['/a'])
    assert tw.get_selected_rows()[0]['row_id'] == '/a'
    tw.set_data([{'row_id': '/z', 'hierarchy_path': ['/z'], 'name': 'Z'}])
    assert tw.get_selected_rows() == []


def test_set_data_keeps_selection_when_configured() -> None:
    tw = TreeWidget(
        columns=_sample_columns(),
        row_id_field='row_id',
        rows=_sample_rows(),
        config=TreeWidgetConfig(clear_selection_on_set_data=False),
    )
    tw.set_selected_row_ids(['/a'])
    tw.set_data([{'row_id': '/z', 'hierarchy_path': ['/z'], 'name': 'Z'}])
    assert tw.get_selected_rows() != []


def test_update_row_replaces_existing() -> None:
    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())
    tw.update_row('/a', {'row_id': '/a', 'hierarchy_path': ['/a'], 'name': 'A2'})
    row = next(r for r in tw._rows if r['row_id'] == '/a')
    assert row['name'] == 'A2'


def test_replace_group_rows_updates_internal_state_without_grid() -> None:
    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())
    tw.replace_group_rows('/a', [{'row_id': '/a', 'hierarchy_path': ['/a'], 'name': 'A-updated'}])
    ids = {r['row_id'] for r in tw._rows}
    assert '/a' in ids
    assert '/a::1' not in ids


def test_get_displayed_rows_falls_back_to_python_rows_before_build() -> None:
    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())
    rows = asyncio.run(tw.get_displayed_rows())
    assert rows == _sample_rows()


def test_get_displayed_rows_uses_run_javascript_for_grid_state(monkeypatch: Any) -> None:
    scripts: list[str] = []

    async def fake_run_javascript(script: str, timeout: float = 1.0) -> list[dict[str, str]]:
        scripts.append(script)
        assert timeout == 5.0
        return [{'row_id': '/b'}, {'row_id': '/a'}]

    monkeypatch.setattr(tree_widget.ui, 'run_javascript', fake_run_javascript)
    tw = TreeWidget(columns=_sample_columns(), row_id_field='row_id', rows=_sample_rows())
    tw._grid = SimpleNamespace(id=77)

    rows = asyncio.run(tw.get_displayed_rows())

    assert rows == [{'row_id': '/b'}, {'row_id': '/a'}]
    assert len(scripts) == 1
    assert 'getElement(77)' in scripts[0]
