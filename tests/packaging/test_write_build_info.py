"""Tests for packaging/write_build_info.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WRITE_BUILD_INFO_PATH = REPO_ROOT / 'packaging' / 'write_build_info.py'


def _load_write_build_info():
    """Load packaging/write_build_info.py as a module.

    Returns:
        Loaded module object.
    """
    spec = importlib.util.spec_from_file_location(
        'cloudscope_write_build_info',
        WRITE_BUILD_INFO_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


write_build_info_mod = _load_write_build_info()


def test_read_project_version_from_pyproject() -> None:
    """Version reader should parse pyproject.toml without tomllib.

    Returns:
        None.
    """
    version = write_build_info_mod.read_project_version(REPO_ROOT)
    assert version
    assert version[0].isdigit()


def test_write_build_info_emits_required_schema(tmp_path: Path) -> None:
    """Writer should emit an importable BUILD_INFO with required keys.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        None.
    """
    output = tmp_path / '_build_info.py'
    written = write_build_info_mod.write_build_info(
        repo_root=REPO_ROOT,
        output_path=output,
    )
    assert written == output
    assert output.is_file()

    namespace: dict = {}
    exec(output.read_text(encoding='utf-8'), namespace)
    build_info = namespace['BUILD_INFO']
    assert isinstance(build_info, dict)
    for key in write_build_info_mod.REQUIRED_BUILD_INFO_KEYS:
        assert key in build_info
    assert build_info['app_name'] == 'CloudScope'
    assert build_info['version'] == write_build_info_mod.read_project_version(REPO_ROOT)
    assert build_info['git_commit']
    assert build_info['git_commit_short']
    assert build_info['git_state'] in {'clean', 'dirty'}


def test_read_project_version_missing_file(tmp_path: Path) -> None:
    """Missing pyproject.toml should fail fast.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        None.
    """
    with pytest.raises(FileNotFoundError):
        write_build_info_mod.read_project_version(tmp_path)


def test_render_build_info_module_requires_keys() -> None:
    """Renderer should reject incomplete BUILD_INFO dicts.

    Returns:
        None.
    """
    with pytest.raises(ValueError, match='missing required keys'):
        write_build_info_mod.render_build_info_module({'app_name': 'CloudScope'})
