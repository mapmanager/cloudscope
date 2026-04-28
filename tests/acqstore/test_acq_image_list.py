"""Unit tests for AcqImageList list/protocol behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from acqstore.acq_image.acq_image_list import AcqImageList, SaveEvent, _build_file_list
from acqstore.acq_image.supported_import_extensions import get_allowed_import_extensions


class _FakeAcqImage:
    """Test double for AcqImage that avoids file IO."""

    def __init__(self, path: str) -> None:
        self.path = str(path)
        self.file_id = self.path
        self._dirty = self.path.endswith('dirty.tif')
        self._saved = 0
        self._default_roi = 1 if self.path.endswith('roi.tif') else None

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def save(self) -> None:
        self._saved += 1
        self._dirty = False

    def get_default_channel(self) -> int | None:
        return 0

    def get_default_roi(self) -> int | None:
        return self._default_roi

    def get_schema_row(self) -> dict[str, object]:
        return {
            'name': Path(self.path).name,
            'path': self.path,
            'num_channels': 1,
            'num_rois': 0 if self._default_roi is None else 1,
        }

    @property
    def saved_count(self) -> int:
        return self._saved


def test_builds_sorted_files_for_directory(tmp_path: Path) -> None:
    (tmp_path / 'b.tif').write_text('')
    (tmp_path / 'a.tif').write_text('')
    (tmp_path / 'ignore.txt').write_text('')

    file_list = AcqImageList(str(tmp_path), file_factory=_FakeAcqImage)

    assert [Path(item.file_id).name for item in file_list.get_files()] == ['a.tif', 'b.tif']


def test_directory_walk_case_insensitive_includes_czi_excludes_tiff(tmp_path: Path) -> None:
    (tmp_path / 'a.CZI').write_text('')
    (tmp_path / 'b.TIF').write_text('')
    (tmp_path / 'c.oir').write_text('')
    (tmp_path / 'ignored.tiff').write_text('')
    (tmp_path / 'skip.txt').write_text('')

    file_list = AcqImageList(str(tmp_path), file_factory=_FakeAcqImage)

    assert [Path(p).name for p in file_list.file_list] == ['a.CZI', 'b.TIF', 'c.oir']


def test_lookup_and_default_selection(tmp_path: Path) -> None:
    file_path = tmp_path / 'sample_roi.tif'
    file_path.write_text('')

    file_list = AcqImageList(str(file_path), file_factory=_FakeAcqImage)

    default_file_id, channel, roi_id = file_list.get_default_selection()
    assert default_file_id == str(file_path.resolve())
    assert channel == 0
    assert roi_id == 1
    assert file_list.has_file_id(default_file_id)
    assert file_list.get_file_by_id(default_file_id) is not None
    assert file_list.get_file_by_index(0).file_id == default_file_id


def test_iter_save_all_yields_progress_and_honors_cancel(tmp_path: Path) -> None:
    first = tmp_path / 'first_dirty.tif'
    second = tmp_path / 'second_dirty.tif'
    first.write_text('')
    second.write_text('')

    file_list = AcqImageList(str(tmp_path), file_factory=_FakeAcqImage)

    cancelled_once = {'called': False}

    def should_cancel() -> bool:
        if cancelled_once['called']:
            return True
        cancelled_once['called'] = True
        return False

    events = list(file_list.iter_save_all(should_cancel=should_cancel))
    assert [event.event for event in events] == [SaveEvent.SAVING, SaveEvent.SAVED, SaveEvent.CANCELLED]
    assert events[-1].completed == 1


def test_get_schema_rows_match_backend_schema(tmp_path: Path) -> None:
    file_path = tmp_path / 'sample.tif'
    file_path.write_text('')
    file_list = AcqImageList(str(file_path), file_factory=_FakeAcqImage)

    rows = file_list.get_schema_rows()
    assert list(rows[0].keys()) == ['name', 'path', 'num_channels', 'num_rois']


def test_build_file_list_folder_depth_one_skips_subdirs(tmp_path: Path) -> None:
    (tmp_path / 'root.tif').write_text('')
    sub = tmp_path / 'sub'
    sub.mkdir()
    (sub / 'nested.tif').write_text('')

    exts = get_allowed_import_extensions()
    shallow = _build_file_list(tmp_path, exts, folder_depth=1)
    assert [Path(p).name for p in shallow] == ['root.tif']

    deeper = _build_file_list(tmp_path, exts, folder_depth=2)
    assert {Path(p).name for p in deeper} == {'nested.tif', 'root.tif'}


def test_build_file_list_folder_depth_three_reaches_two_levels_down(tmp_path: Path) -> None:
    (tmp_path / 'a.tif').write_text('')
    sub = tmp_path / 'sub'
    sub.mkdir()
    (sub / 'b.tif').write_text('')
    deep = sub / 'deep'
    deep.mkdir()
    (deep / 'c.tif').write_text('')

    exts = get_allowed_import_extensions()
    two = _build_file_list(tmp_path, exts, folder_depth=2)
    assert {Path(p).name for p in two} == {'a.tif', 'b.tif'}

    three = _build_file_list(tmp_path, exts, folder_depth=3)
    assert {Path(p).name for p in three} == {'a.tif', 'b.tif', 'c.tif'}


def test_build_file_list_rejects_non_positive_depth(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='folder_depth'):
        _build_file_list(tmp_path, ['tif'], folder_depth=0)


def test_acq_image_list_rejects_non_positive_folder_depth(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='folder_depth'):
        AcqImageList(str(tmp_path), file_factory=_FakeAcqImage, folder_depth=0)


def test_load_safe_csv_rel_path_parent_resolution_and_warnings(tmp_path: Path) -> None:
    csv_dir = tmp_path / 'csvroot'
    csv_dir.mkdir()
    valid = csv_dir / 'ok.tif'
    valid.write_text('')
    csv_path = csv_dir / 'list.csv'
    csv_path.write_text(
        'rel_path\n'
        'ok.tif\n'
        '   \n'
        'missing.tif\n',
        encoding='utf-8',
    )

    result = AcqImageList.load_safe(
        str(csv_path),
        kind='csv',
        file_factory=_FakeAcqImage,
    )
    assert len(result.acq_image_list) == 1
    assert Path(result.acq_image_list.get_files()[0].file_id).name == 'ok.tif'
    assert len(result.warnings) == 2
    assert any('blank rel_path' in warning.message for warning in result.warnings)
    assert any('does not exist' in warning.message for warning in result.warnings)


def test_load_safe_csv_missing_required_column_warns(tmp_path: Path) -> None:
    csv_path = tmp_path / 'bad.csv'
    csv_path.write_text('path\nfoo.tif\n', encoding='utf-8')
    result = AcqImageList.load_safe(str(csv_path), kind='csv', file_factory=_FakeAcqImage)
    assert len(result.acq_image_list) == 0
    assert len(result.warnings) == 1
    assert 'missing required column "rel_path"' in result.warnings[0].message


def test_load_safe_file_missing_returns_warning_not_exception(tmp_path: Path) -> None:
    missing = tmp_path / 'missing.tif'
    result = AcqImageList.load_safe(str(missing), kind='file', file_factory=_FakeAcqImage)
    assert len(result.acq_image_list) == 0
    assert len(result.warnings) == 1
    assert 'does not exist' in result.warnings[0].message
