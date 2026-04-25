from pathlib import Path

import pytest

from acqstore.acq_image.import_paths import find_import_paths


def test_find_import_paths_returns_single_tif_file(tmp_path: Path) -> None:
    file_path = tmp_path / "image.tif"
    file_path.write_text("", encoding="utf-8")

    result = find_import_paths(str(file_path))

    assert result == [str(file_path.resolve())]


def test_find_import_paths_returns_single_oir_file(tmp_path: Path) -> None:
    file_path = tmp_path / "image.oir"
    file_path.write_text("", encoding="utf-8")

    result = find_import_paths(str(file_path))

    assert result == [str(file_path.resolve())]


def test_find_import_paths_accepts_uppercase_tif_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "image.TIF"
    file_path.write_text("", encoding="utf-8")

    result = find_import_paths(str(file_path))

    assert result == [str(file_path.resolve())]


def test_find_import_paths_raises_for_unsupported_file(tmp_path: Path) -> None:
    file_path = tmp_path / "image.txt"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported acquisition file"):
        find_import_paths(str(file_path))


def test_find_import_paths_raises_for_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.tif"

    with pytest.raises(FileNotFoundError, match="Path does not exist"):
        find_import_paths(str(missing_path))


def test_find_import_paths_filters_supported_directory_files(tmp_path: Path) -> None:
    tif_path = tmp_path / "b_image.tif"
    oir_path = tmp_path / "a_image.oir"
    txt_path = tmp_path / "notes.txt"
    tif_path.write_text("", encoding="utf-8")
    oir_path.write_text("", encoding="utf-8")
    txt_path.write_text("", encoding="utf-8")

    result = find_import_paths(str(tmp_path))

    assert result == [str(oir_path.resolve()), str(tif_path.resolve())]


def test_find_import_paths_returns_sorted_absolute_directory_paths(tmp_path: Path) -> None:
    later_path = tmp_path / "z_last.oir"
    earlier_path = tmp_path / "a_first.tif"
    later_path.write_text("", encoding="utf-8")
    earlier_path.write_text("", encoding="utf-8")

    result = find_import_paths(str(tmp_path))

    assert result == sorted(result)
    assert result == [str(earlier_path.resolve()), str(later_path.resolve())]


def test_find_import_paths_raises_for_directory_without_supported_files(
    tmp_path: Path,
) -> None:
    unsupported_path = tmp_path / "notes.txt"
    unsupported_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="No supported acquisition files found"):
        find_import_paths(str(tmp_path))
