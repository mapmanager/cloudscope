"""Tests for CloudScope user workspace quota helpers."""

from __future__ import annotations

import pytest

from cloudscope.quota import QuotaExceededError, StorageQuota, directory_size_bytes, ensure_within_quota, mb_to_bytes


def test_directory_size_bytes_counts_recursive_files(tmp_path) -> None:
    (tmp_path / 'a.bin').write_bytes(b'123')
    nested = tmp_path / 'nested'
    nested.mkdir()
    (nested / 'b.bin').write_bytes(b'45')

    assert directory_size_bytes(tmp_path) == 5


def test_mb_to_bytes_preserves_none_and_converts_mb() -> None:
    assert mb_to_bytes(None) is None
    assert mb_to_bytes(2) == 2 * 1024 * 1024


def test_storage_quota_allows_under_limits(tmp_path) -> None:
    (tmp_path / 'a.bin').write_bytes(b'123')

    StorageQuota(quota_bytes=5, max_upload_bytes=2).check_can_add_file(root=tmp_path, incoming_bytes=2)


def test_storage_quota_rejects_over_total_limit(tmp_path) -> None:
    (tmp_path / 'a.bin').write_bytes(b'123')

    with pytest.raises(QuotaExceededError, match='workspace quota'):
        StorageQuota(quota_bytes=5).check_can_add_file(root=tmp_path, incoming_bytes=3)


def test_storage_quota_rejects_over_single_upload_limit(tmp_path) -> None:
    with pytest.raises(QuotaExceededError, match='file is larger'):
        StorageQuota(quota_bytes=100, max_upload_bytes=5).check_can_add_file(root=tmp_path, incoming_bytes=6)


def test_ensure_within_quota_supports_upload_and_total_limits(tmp_path) -> None:
    (tmp_path / 'a.bin').write_bytes(b'123')

    ensure_within_quota(root=tmp_path, incoming_bytes=2, quota_bytes=5, max_upload_bytes=2)

    with pytest.raises(QuotaExceededError):
        ensure_within_quota(root=tmp_path, incoming_bytes=3, quota_bytes=5, max_upload_bytes=10)
