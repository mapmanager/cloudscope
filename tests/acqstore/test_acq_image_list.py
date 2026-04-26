"""Unit tests for AcqImageList list/protocol behavior."""

from __future__ import annotations

from pathlib import Path

from acqstore.acq_image.acq_image_list import AcqImageList, SaveEvent


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

    @property
    def saved_count(self) -> int:
        return self._saved


def test_builds_sorted_files_for_directory(tmp_path: Path) -> None:
    (tmp_path / 'b.tif').write_text('')
    (tmp_path / 'a.tif').write_text('')
    (tmp_path / 'ignore.txt').write_text('')

    file_list = AcqImageList(str(tmp_path), file_factory=_FakeAcqImage)

    assert [Path(item.file_id).name for item in file_list.get_files()] == ['a.tif', 'b.tif']


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


def test_get_table_schema_matches_backend_schema(tmp_path: Path) -> None:
    file_path = tmp_path / 'sample.tif'
    file_path.write_text('')
    file_list = AcqImageList(str(file_path), file_factory=_FakeAcqImage)

    schema = file_list.get_table_schema()
    assert [column.name for column in schema] == ['path', 'num_channels', 'num_rois']
