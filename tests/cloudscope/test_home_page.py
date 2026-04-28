"""Tests for home-page path-kind inference helpers."""

from __future__ import annotations

from cloudscope.gui.home_page import _infer_load_kind


def test_infer_load_kind_csv_suffix() -> None:
    assert _infer_load_kind('/tmp/list.csv') == 'csv'


def test_infer_load_kind_folder(tmp_path) -> None:
    folder = tmp_path / 'folder'
    folder.mkdir()
    assert _infer_load_kind(str(folder)) == 'folder'

def test_infer_load_kind_defaults_to_file(tmp_path) -> None:
    missing = tmp_path / 'a.tif'
    assert _infer_load_kind(str(missing)) == 'file'
