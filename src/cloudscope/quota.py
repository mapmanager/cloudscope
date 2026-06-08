"""Small filesystem quota helpers for CloudScope user workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class QuotaExceededError(RuntimeError):
    """Raised when an operation would exceed a configured workspace quota."""


def directory_size_bytes(path: Path) -> int:
    """Return recursive size in bytes for files under ``path``.

    Missing paths count as zero. Files that disappear while scanning are ignored.
    """
    root = Path(path)
    if not root.exists():
        return 0
    if root.is_file():
        try:
            return root.stat().st_size
        except OSError:
            return 0

    total = 0
    for child in root.rglob('*'):
        if not child.is_file():
            continue
        try:
            total += child.stat().st_size
        except OSError:
            continue
    return total


def mb_to_bytes(value_mb: int | None) -> int | None:
    """Convert megabytes to bytes, preserving ``None`` as unlimited."""
    if value_mb is None:
        return None
    return int(value_mb) * 1024 * 1024


@dataclass(frozen=True, slots=True)
class StorageQuota:
    """Optional upload and total-storage limits for a user workspace."""

    quota_bytes: int | None = None
    max_upload_bytes: int | None = None

    def check_can_add_file(self, *, root: Path, incoming_bytes: int) -> None:
        """Raise if adding one file would exceed configured limits.

        Args:
            root: Workspace root counted against the total quota.
            incoming_bytes: Number of bytes about to be added.

        Raises:
            QuotaExceededError: If the file or workspace quota would be exceeded.
        """
        incoming = max(0, int(incoming_bytes))
        if self.max_upload_bytes is not None and incoming > int(self.max_upload_bytes):
            raise QuotaExceededError(
                'Upload rejected: file is larger than the configured limit '
                f'({incoming} bytes > {self.max_upload_bytes} bytes).'
            )
        if self.quota_bytes is None:
            return
        used = directory_size_bytes(Path(root))
        if used + incoming <= int(self.quota_bytes):
            return
        raise QuotaExceededError(
            'Upload rejected: workspace quota would be exceeded '
            f'(used {used} bytes, incoming {incoming} bytes, limit {self.quota_bytes} bytes).'
        )


def ensure_within_quota(
    *,
    root: Path,
    incoming_bytes: int,
    quota_bytes: int | None,
    max_upload_bytes: int | None = None,
) -> None:
    """Backward-compatible helper for checking one pending file addition."""
    StorageQuota(quota_bytes=quota_bytes, max_upload_bytes=max_upload_bytes).check_can_add_file(
        root=root,
        incoming_bytes=incoming_bytes,
    )
