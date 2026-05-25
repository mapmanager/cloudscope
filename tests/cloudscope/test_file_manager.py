"""Tests for platform file-manager reveal commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cloudscope.utils import file_manager


def test_reveal_in_file_manager_raises_for_missing_path(tmp_path: Path) -> None:
    """Missing paths should fail before launching a platform command."""
    with pytest.raises(FileNotFoundError):
        file_manager.reveal_in_file_manager(tmp_path / "missing.tif")


def test_reveal_in_file_manager_uses_macos_open(monkeypatch: Any, tmp_path: Path) -> None:
    """macOS should reveal and select the path in Finder."""
    target = tmp_path / "a.tif"
    target.write_text("x")
    calls: list[tuple[list[str], bool, bool]] = []
    monkeypatch.setattr(file_manager.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(file_manager.subprocess, "run", lambda cmd, check=False, shell=False: calls.append((cmd, check, shell)))

    file_manager.reveal_in_file_manager(target)

    assert calls == [(["open", "-R", str(target.resolve())], False, False)]


def test_reveal_in_file_manager_uses_windows_explorer(monkeypatch: Any, tmp_path: Path) -> None:
    """Windows should ask Explorer to select the path."""
    target = tmp_path / "a.tif"
    target.write_text("x")
    calls: list[tuple[list[str], bool, bool]] = []
    monkeypatch.setattr(file_manager.platform, "system", lambda: "Windows")
    monkeypatch.setattr(file_manager.subprocess, "run", lambda cmd, check=False, shell=False: calls.append((cmd, check, shell)))

    file_manager.reveal_in_file_manager(target)

    assert calls == [(["explorer", f'/select,"{target.resolve()}"'], False, True)]


def test_reveal_in_file_manager_uses_linux_folder(monkeypatch: Any, tmp_path: Path) -> None:
    """Linux should open the containing folder for file paths."""
    target = tmp_path / "a.tif"
    target.write_text("x")
    calls: list[tuple[list[str], bool, bool]] = []
    monkeypatch.setattr(file_manager.platform, "system", lambda: "Linux")
    monkeypatch.setattr(file_manager.subprocess, "run", lambda cmd, check=False, shell=False: calls.append((cmd, check, shell)))

    file_manager.reveal_in_file_manager(target)

    assert calls == [(["xdg-open", str(tmp_path.resolve())], False, False)]
