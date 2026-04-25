"""Acquisition-file list contract for CloudScope."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Protocol

from .acq_file import AcqFileProtocol
from .common import TableColumnSchema


class AcqFileListProtocol(Protocol):
    """Backend-facing ordered collection of acquisition files."""

    def __len__(self) -> int:
        """Return number of files in the collection."""

    def __iter__(self) -> Iterator[AcqFileProtocol]:
        """Iterate files in stable display order."""

    def get_files(self) -> Sequence[AcqFileProtocol]:
        """Return files in stable display order."""

    def get_file_by_id(self, file_id: str) -> AcqFileProtocol | None:
        """Return one file by stable identifier.

        Args:
            file_id: Stable file identifier.

        Returns:
            Matching file object, or ``None`` when the identifier does not
            exist in the collection.
        """

    def get_file_by_index(self, index: int) -> AcqFileProtocol:
        """Return one file by stable display index.

        Args:
            index: Zero-based display index.

        Returns:
            Matching file object.

        Raises:
            IndexError: If the display index is out of range.
        """

    def has_file_id(self, file_id: str) -> bool:
        """Return whether the file identifier exists in the collection."""

    def get_default_file_id(self) -> str | None:
        """Return the explicitly defined default file identifier, if any."""

    def get_default_selection(self) -> tuple[str | None, int | None, str | None]:
        """Return default primary selection for initial app state.

        Returns:
            Tuple of ``(file_id, channel, roi_id)`` using backend-native values.
            Any tuple member may be ``None`` when no explicit default exists.
        """

    def get_dirty_files(self) -> Sequence[AcqFileProtocol]:
        """Return dirty files in stable display order."""

    def has_dirty_files(self) -> bool:
        """Return whether any file in the collection is dirty."""

    def save_all(self) -> None:
        """Persist all dirty files in the collection."""

    def get_table_schema(self) -> Sequence[TableColumnSchema]:
        """Return semantic table-column schema for file-list views.

        Returns:
            Ordered semantic table column schema entries. The GUI adapts these to
            AG Grid column definitions.
        """
