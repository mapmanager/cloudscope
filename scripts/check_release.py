#!/usr/bin/env python3
"""Validate CloudScope release metadata before tagging or publishing.

Local use:
    python scripts/check_release.py v0.1.0

CI use:
    python scripts/check_release.py --ci v0.1.0
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

TAG_RE = re.compile(r'^v(?P<version>\d+\.\d+\.\d+(?:[a-zA-Z0-9.-]+)?)$')
ROOT = Path(__file__).resolve().parents[1]


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['git', *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def fail(message: str) -> None:
    print(f'ERROR: {message}', file=sys.stderr)
    raise SystemExit(1)


def read_project_version() -> str:
    pyproject_path = ROOT / 'pyproject.toml'
    if not pyproject_path.exists():
        fail('pyproject.toml was not found.')
    with pyproject_path.open('rb') as f:
        data = tomllib.load(f)
    try:
        version = data['project']['version']
    except KeyError:
        fail('pyproject.toml does not define [project].version.')
    if not isinstance(version, str) or not version:
        fail('[project].version in pyproject.toml must be a non-empty string.')
    return version


def check_tag_format(tag: str) -> str:
    match = TAG_RE.match(tag)
    if not match:
        fail(f'tag must look like vX.Y.Z, got {tag!r}.')
    return match.group('version')


def check_version_matches_tag(tag: str) -> None:
    tag_version = check_tag_format(tag)
    project_version = read_project_version()
    if project_version != tag_version:
        fail(f'tag {tag!r} does not match pyproject.toml version {project_version!r}.')
    print(f'OK: tag {tag!r} matches pyproject.toml version {project_version!r}.')


def check_changelog_has_version(tag: str) -> None:
    version = tag.removeprefix('v')
    changelog_path = ROOT / 'CHANGELOG.md'
    if not changelog_path.exists():
        fail('CHANGELOG.md was not found.')
    changelog = changelog_path.read_text(encoding='utf-8')
    patterns = [f'## [{version}]', f'## [{version}] - ']
    if not any(pattern in changelog for pattern in patterns):
        fail(f'CHANGELOG.md does not contain a section for [{version}].')
    print(f'OK: CHANGELOG.md contains a section for [{version}].')


def check_on_main_branch() -> None:
    result = run_git(['branch', '--show-current'])
    branch = result.stdout.strip()
    if branch != 'main':
        fail(f'current branch must be main, got {branch!r}.')
    print('OK: current branch is main.')


def check_working_tree_clean() -> None:
    result = run_git(['status', '--porcelain'])
    if result.stdout.strip():
        fail('working tree is not clean. Commit or stash changes before tagging.')
    print('OK: working tree is clean.')


def check_local_tag_absent(tag: str) -> None:
    result = run_git(['rev-parse', '--verify', f'refs/tags/{tag}'], check=False)
    if result.returncode == 0:
        fail(f'local tag {tag!r} already exists.')
    print(f'OK: local tag {tag!r} does not exist yet.')


def check_remote_tag_absent(tag: str) -> None:
    result = run_git(['ls-remote', '--tags', 'origin', f'refs/tags/{tag}'], check=False)
    if result.returncode != 0:
        fail(f'could not query origin for tags: {result.stderr.strip()}')
    if result.stdout.strip():
        fail(f'origin already has tag {tag!r}.')
    print(f'OK: origin does not have tag {tag!r}.')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate CloudScope release metadata.')
    parser.add_argument('tag', help='Release tag, for example v0.1.0')
    parser.add_argument(
        '--ci',
        action='store_true',
        help='Skip local-only checks such as current branch, clean tree, and tag absence.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tag = args.tag.strip()

    check_version_matches_tag(tag)
    check_changelog_has_version(tag)

    if not args.ci:
        check_on_main_branch()
        check_working_tree_clean()
        check_local_tag_absent(tag)
        check_remote_tag_absent(tag)

    print('OK: release metadata checks passed.')


if __name__ == '__main__':
    main()
