from __future__ import annotations

from pathlib import Path
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
import os
from typing import TYPE_CHECKING

from acqstore.schema import (
    ACQ_FILE_LIST_SCHEMA,
    SchemaDefinition,
    validate_values_for_schema,
)

from .supported_import_extensions import get_allowed_import_extensions

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage

def _build_file_list(path: str | Path, file_types: Sequence[str]) -> list[str]:
    """Build a list of files in the given path.

    Recursively traverse into path and build a list of files with the given types.

    Args:
        path: The path to traverse.
        file_types: The types of files to include in the list (no dot extension)

    Returns:
        A list of absolute file paths.
    """
    allowed_exts = {f".{ext.lower().lstrip('.')}" for ext in file_types}
    result: list[str] = []

    for root, _dirs, filenames in os.walk(str(path)):
        for filename in filenames:
            file_path = Path(root) / filename
            if file_path.suffix.lower() in allowed_exts:
                result.append(str(file_path.resolve()))
    return sorted(result)


class SaveEvent(StrEnum):
    """Save lifecycle event type for list-level save iteration."""

    SAVING = 'saving'
    SAVED = 'saved'
    CANCELLED = 'cancelled'


@dataclass(frozen=True, slots=True)
class SaveProgress:
    """Progress event emitted while iterating list saves.

    Attributes:
        event: Save lifecycle event type.
        completed: Number of files saved so far.
        total: Number of dirty files planned for save.
        file_id: File identifier associated with this event.
    """

    event: SaveEvent
    completed: int
    total: int
    file_id: str | None

class AcqImageList:
    """Backend-facing ordered collection of acquisition files."""

    def __init__(
        self,
        path: str,
        *,
        file_factory: Callable[[str], AcqImage] | None = None,
    ):
        """Load one file or recursively load a directory of files.

        Args:
            path: Filesystem path to one file or directory.
            file_factory: Optional factory for creating file objects. Defaults to
                ``AcqImage``.
        """
        self.path = str(path)

        if os.path.isdir(path):
            self.file_list = _build_file_list(path, get_allowed_import_extensions())
        else:
            self.file_list = [str(Path(path).resolve())]

        if file_factory is None:
            from acqstore.acq_image.acq_image import AcqImage

            file_factory = AcqImage
        self._files = [file_factory(file_path) for file_path in self.file_list]
        self._files_by_id = {acq_file.file_id: acq_file for acq_file in self._files}

    def __len__(self) -> int:
        """Return number of files in the collection."""
        return len(self._files)

    def __iter__(self) -> Iterator[AcqImage]:
        """Iterate files in stable display order."""
        return iter(self._files)

    def get_files(self) -> Sequence[AcqImage]:
        """Return files in stable display order."""
        return tuple(self._files)

    def get_file_by_id(self, file_id: str) -> AcqImage | None:
        """Return one file by stable identifier.

        Args:
            file_id: Stable file identifier.

        Returns:
            Matching file object, or ``None`` when not found.
        """
        return self._files_by_id.get(file_id)

    def get_file_by_index(self, index: int) -> AcqImage:
        """Return one file by stable display index.

        Args:
            index: Zero-based display index.

        Returns:
            Matching file object.

        Raises:
            IndexError: If the display index is out of range.
        """
        return self._files[index]

    def has_file_id(self, file_id: str) -> bool:
        """Return whether the file identifier exists in the collection."""
        return file_id in self._files_by_id

    def get_default_file_id(self) -> str | None:
        """Return the default file identifier in stable display order.
        
        Returns first file in list."""
        if not self._files:
            return None
        return self._files[0].file_id

    def get_default_selection(self) -> tuple[str | None, int | None, int | None]:
        """Return default primary selection for initial app state.
        
        Returns:
            Tuple of (file_id, channel, roi) using backend-native values.
            Any tuple member may be None when no explicit default exists.
        """
        default_file_id = self.get_default_file_id()
        if default_file_id is None:
            return (None, None, None)
        acq_file = self._files_by_id[default_file_id]
        return (
            default_file_id,
            acq_file.get_default_channel(),
            acq_file.get_default_roi(),
        )

    def get_dirty_files(self) -> Sequence[AcqImage]:
        """Return dirty files in stable display order."""
        return tuple(acq_file for acq_file in self._files if acq_file.is_dirty)

    def has_dirty_files(self) -> bool:
        """Return whether any file in the collection is dirty."""
        return any(acq_file.is_dirty for acq_file in self._files)

    def iter_save_all(
        self,
        *,
        should_cancel: Callable[[], bool] | None = None,
    ) -> Iterator[SaveProgress]:
        """Persist dirty files while yielding progress events.

        Args:
            should_cancel: Optional callback checked between file saves. Return
                True to stop iteration early.

        Yields:
            Save progress events for save start/finish and cancellation.
        """
        dirty_files = list(self.get_dirty_files())
        total = len(dirty_files)
        completed = 0

        for acq_file in dirty_files:
            if should_cancel is not None and should_cancel():
                yield SaveProgress(
                    event=SaveEvent.CANCELLED,
                    completed=completed,
                    total=total,
                    file_id=acq_file.file_id,
                )
                return

            yield SaveProgress(
                event=SaveEvent.SAVING,
                completed=completed,
                total=total,
                file_id=acq_file.file_id,
            )
            acq_file.save()
            completed += 1
            yield SaveProgress(
                event=SaveEvent.SAVED,
                completed=completed,
                total=total,
                file_id=acq_file.file_id,
            )

    def save_all(self, *, should_cancel: Callable[[], bool] | None = None) -> None:
        """Persist all dirty files in the collection.

        Args:
            should_cancel: Optional callback checked between file saves.
        """
        for _event in self.iter_save_all(should_cancel=should_cancel):
            continue

    def get_schema(self) -> SchemaDefinition:
        """Return schema definition for rows in this list."""
        return ACQ_FILE_LIST_SCHEMA

    def get_schema_rows(self) -> list[dict[str, object]]:
        """Return schema-keyed rows for all files in stable display order.

        Returns:
            List of row dictionaries keyed by schema field name.

        Raises:
            KeyError: If a required schema field is missing from any row.
            ValueError: If any row has keys not declared by the schema.
        """
        schema = self.get_schema()
        rows = [acq_file.get_schema_row() for acq_file in self.get_files()]
        for row in rows:
            validate_values_for_schema(schema, row)
        return rows