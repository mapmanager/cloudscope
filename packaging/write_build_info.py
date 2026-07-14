#!/usr/bin/env python3
"""Write CloudScope runtime build metadata for packaging and web deploys.

Generates ``src/cloudscope/_build_info.py`` with a ``BUILD_INFO`` dict matching
the schema used by macOS packaging and Windows CI. Compatible with Python 3.10+
(stdlib only; does not require ``tomllib`` or project dependencies).

The generated file is transient and must not be committed.
"""

from __future__ import annotations

import argparse
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

REQUIRED_BUILD_INFO_KEYS = (
    'app_name',
    'version',
    'git_tag',
    'git_commit',
    'git_commit_short',
    'git_branch',
    'git_state',
    'build_timestamp_utc',
    'build_timestamp_local',
    'build_bundle_version',
    'python_version',
    'nicegui_version',
    'pyinstaller_version',
    'platform',
)

_VERSION_RE = re.compile(
    r'^version\s*=\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)


def default_repo_root() -> Path:
    """Return the repository root inferred from this file location.

    Returns:
        Absolute path to the CloudScope repository root.
    """
    return Path(__file__).resolve().parent.parent


def default_output_path(repo_root: Path) -> Path:
    """Return the default generated build-info module path.

    Args:
        repo_root: Repository root directory.

    Returns:
        Path to ``src/cloudscope/_build_info.py``.
    """
    return repo_root / 'src' / 'cloudscope' / '_build_info.py'


def read_project_version(repo_root: Path) -> str:
    """Read the project version from ``pyproject.toml`` without ``tomllib``.

    Args:
        repo_root: Repository root directory.

    Returns:
        Project version string.

    Raises:
        FileNotFoundError: If ``pyproject.toml`` is missing.
        ValueError: If no ``version = "..."`` line is found.
    """
    pyproject = repo_root / 'pyproject.toml'
    if not pyproject.is_file():
        raise FileNotFoundError(f'pyproject.toml not found: {pyproject}')
    text = pyproject.read_text(encoding='utf-8')
    match = _VERSION_RE.search(text)
    if match is None:
        raise ValueError(f'no project version found in {pyproject}')
    return match.group(1)


def _git(repo_root: Path, *args: str) -> str:
    """Run a git command in ``repo_root`` and return stripped stdout.

    Args:
        repo_root: Repository root directory.
        *args: Arguments passed to ``git``.

    Returns:
        Command stdout with surrounding whitespace removed, or ``""`` on error.
    """
    try:
        return subprocess.check_output(
            ['git', *args],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ''


def _package_version(package_name: str) -> str:
    """Return an installed package version when available.

    Args:
        package_name: Distribution package name.

    Returns:
        Installed version or ``"unknown"``.
    """
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return 'unknown'


def collect_build_info(
    repo_root: Path,
    *,
    app_name: str = 'CloudScope',
) -> dict[str, Any]:
    """Collect build metadata for the current checkout and Python environment.

    Args:
        repo_root: Repository root directory.
        app_name: Human-readable application name.

    Returns:
        Build metadata dictionary matching the packaged ``BUILD_INFO`` schema.
    """
    version = read_project_version(repo_root)
    git_commit = _git(repo_root, 'rev-parse', 'HEAD') or 'unknown'
    git_commit_short = _git(repo_root, 'rev-parse', '--short', 'HEAD') or 'unknown'
    git_branch = _git(repo_root, 'symbolic-ref', '--short', '-q', 'HEAD') or 'detached'
    git_tag_raw = _git(repo_root, 'describe', '--tags', '--exact-match', 'HEAD')
    git_tag = git_tag_raw if git_tag_raw else None
    git_state = 'dirty' if _git(repo_root, 'status', '--porcelain') else 'clean'
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    now_local = datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')

    return {
        'app_name': app_name,
        'version': version,
        'git_tag': git_tag,
        'git_commit': git_commit,
        'git_commit_short': git_commit_short,
        'git_branch': git_branch,
        'git_state': git_state,
        'build_timestamp_utc': now_utc,
        'build_timestamp_local': now_local,
        'build_bundle_version': version,
        'python_version': platform.python_version(),
        'nicegui_version': _package_version('nicegui'),
        'pyinstaller_version': _package_version('pyinstaller'),
        'platform': platform.platform(),
    }


def render_build_info_module(build_info: dict[str, Any]) -> str:
    """Render a Python module text that defines ``BUILD_INFO``.

    Args:
        build_info: Build metadata dictionary.

    Returns:
        Source text for ``_build_info.py``.

    Raises:
        ValueError: If required keys are missing.
    """
    missing = [key for key in REQUIRED_BUILD_INFO_KEYS if key not in build_info]
    if missing:
        raise ValueError(f'BUILD_INFO missing required keys: {missing}')
    return (
        '"""Auto-generated build metadata.\n\n'
        'Generated by packaging/write_build_info.py. '
        'Do not edit or commit this file.\n'
        '"""\n\n'
        f'BUILD_INFO = {build_info!r}\n'
    )


def write_build_info(
    repo_root: Path | None = None,
    *,
    output_path: Path | None = None,
    app_name: str = 'CloudScope',
) -> Path:
    """Write the generated ``_build_info.py`` module.

    Args:
        repo_root: Repository root. Defaults to parent of ``packaging/``.
        output_path: Destination module path. Defaults under ``src/cloudscope/``.
        app_name: Human-readable application name.

    Returns:
        Path to the written module.
    """
    root = (repo_root or default_repo_root()).resolve()
    destination = (output_path or default_output_path(root)).resolve()
    build_info = collect_build_info(root, app_name=app_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_build_info_module(build_info), encoding='utf-8')
    return destination


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument vector. Defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code (``0`` on success).
    """
    parser = argparse.ArgumentParser(
        description='Write src/cloudscope/_build_info.py for packaging/web deploys.',
    )
    parser.add_argument(
        '--repo-root',
        type=Path,
        default=None,
        help='Repository root (default: parent of packaging/).',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output path for _build_info.py.',
    )
    parser.add_argument(
        '--app-name',
        default='CloudScope',
        help='Application name stored in BUILD_INFO.',
    )
    args = parser.parse_args(argv)

    path = write_build_info(
        repo_root=args.repo_root,
        output_path=args.output,
        app_name=args.app_name,
    )
    # Re-load for log lines without importing as a package.
    namespace: dict[str, Any] = {}
    exec(path.read_text(encoding='utf-8'), namespace)
    info = namespace['BUILD_INFO']
    print(f'[build-info] Wrote {path}')
    print(f'[build-info] Version : {info.get("version")}')
    print(f'[build-info] Commit  : {info.get("git_commit_short")}')
    print(f'[build-info] Tag     : {info.get("git_tag") or "none"}')
    print(f'[build-info] State   : {info.get("git_state")}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
