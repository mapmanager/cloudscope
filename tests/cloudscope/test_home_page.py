"""Tests for home-page path-kind inference helpers."""

from __future__ import annotations

from cloudscope.events.files import LoadPathKind
from cloudscope.runtime import infer_load_kind


def test_infer_load_kind_csv_suffix() -> None:
    assert infer_load_kind('/tmp/list.csv') is LoadPathKind.CSV


def test_infer_load_kind_folder(tmp_path) -> None:
    folder = tmp_path / 'folder'
    folder.mkdir()
    assert infer_load_kind(str(folder)) is LoadPathKind.FOLDER

def test_infer_load_kind_defaults_to_file(tmp_path) -> None:
    missing = tmp_path / 'a.tif'
    assert infer_load_kind(str(missing)) is LoadPathKind.FILE
