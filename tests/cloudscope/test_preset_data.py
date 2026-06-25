"""Tests for docker/remote preset dataset path helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudscope.preset_data import (
    PRESET_MANNING_ENV,
    get_manning_preset_path,
    is_loadable_preset_folder,
)


def test_get_manning_preset_path_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PRESET_MANNING_ENV, raising=False)
    assert get_manning_preset_path() is None


def test_get_manning_preset_path_reads_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    preset = tmp_path / 'manning'
    monkeypatch.setenv(PRESET_MANNING_ENV, str(preset))
    assert get_manning_preset_path() == preset


def test_is_loadable_preset_folder_false_for_missing_path(tmp_path: Path) -> None:
    assert is_loadable_preset_folder(tmp_path / 'missing') is False


def test_is_loadable_preset_folder_false_for_empty_directory(tmp_path: Path) -> None:
    folder = tmp_path / 'empty'
    folder.mkdir()
    assert is_loadable_preset_folder(folder) is False


def test_is_loadable_preset_folder_true_when_importable_file_exists(tmp_path: Path) -> None:
    folder = tmp_path / 'dataset'
    folder.mkdir()
    (folder / 'sample.tif').write_bytes(b'x')
    assert is_loadable_preset_folder(folder) is True
