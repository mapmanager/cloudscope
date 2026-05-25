"""Tests for file-list context-menu actions."""

from __future__ import annotations

from typing import Any

from cloudscope.views import file_list_view


class _FakeTable:
    """Minimal TableWidget stand-in for context-menu tests."""

    def __init__(self, selected_rows: list[dict[str, Any]]) -> None:
        """Create the fake table.

        Args:
            selected_rows: Rows returned by ``get_selected_rows``.
        """
        self._selected_rows = selected_rows

    def get_selected_rows(self) -> list[dict[str, Any]]:
        """Return configured selected rows."""
        return list(self._selected_rows)


def test_reveal_selected_file_uses_selected_row_path(monkeypatch: Any) -> None:
    """Reveal In Finder should use the selected row's row-id field path."""
    revealed: list[str] = []
    monkeypatch.setattr(file_list_view, "reveal_in_file_manager", lambda path: revealed.append(path))
    view = object.__new__(file_list_view.AcqImageListTableView)
    view._table = _FakeTable([{"path": "/tmp/a.tif"}])
    view._row_id_field = "path"

    view._reveal_selected_file_in_finder()

    assert revealed == ["/tmp/a.tif"]


def test_reveal_selected_file_no_selection_does_not_reveal(monkeypatch: Any) -> None:
    """Reveal In Finder should be a no-op when there is no selected row."""
    revealed: list[str] = []
    notified: list[tuple[str, str]] = []
    monkeypatch.setattr(file_list_view, "reveal_in_file_manager", lambda path: revealed.append(path))
    monkeypatch.setattr(file_list_view.ui, "notify", lambda message, type="info": notified.append((message, type)))
    view = object.__new__(file_list_view.AcqImageListTableView)
    view._table = _FakeTable([])
    view._row_id_field = "path"

    view._reveal_selected_file_in_finder()

    assert revealed == []
    assert notified == [("No file selected", "warning")]


def test_reveal_selected_file_missing_path_notifies(monkeypatch: Any) -> None:
    """Reveal In Finder should warn when the selected row has no path."""
    revealed: list[str] = []
    notified: list[tuple[str, str]] = []
    monkeypatch.setattr(file_list_view, "reveal_in_file_manager", lambda path: revealed.append(path))
    monkeypatch.setattr(file_list_view.ui, "notify", lambda message, type="info": notified.append((message, type)))
    view = object.__new__(file_list_view.AcqImageListTableView)
    view._table = _FakeTable([{"name": "a.tif"}])
    view._row_id_field = "path"

    view._reveal_selected_file_in_finder()

    assert revealed == []
    assert notified == [("Selected row has no file path", "warning")]
