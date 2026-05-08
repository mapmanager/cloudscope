from __future__ import annotations

import os
import csv
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from acqstore.schema import (
    ACQ_FILE_LIST_SCHEMA,
    SchemaDefinition,
    validate_values_for_schema,
)

from .supported_import_extensions import get_allowed_import_extensions

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


def _build_file_list(path: str | Path, file_types: Sequence[str], *, folder_depth: int = 4) -> list[str]:
    """Build a list of files under ``path`` up to a bounded directory depth.

    Depth is 1-based from ``path``: depth ``1`` collects only files directly in
    ``path``; depth ``2`` also includes files in immediate child directories; and so
    on, up to ``folder_depth``.

    Args:
        path: Directory to traverse (must be a directory when called from
            :class:`AcqImageList`).
        file_types: Extensions to include (no leading dot).
        folder_depth: Maximum directory depth to visit (must be >= 1).

    Returns:
        Sorted list of absolute file paths.

    Raises:
        ValueError: If ``folder_depth`` is less than 1.
    """
    if folder_depth < 1:
        raise ValueError(f'folder_depth must be >= 1, got {folder_depth}')
    allowed_exts = {f'.{ext.lower().lstrip(".")}' for ext in file_types}
    result: list[str] = []
    root = Path(path).resolve()
    queue: deque[tuple[Path, int]] = deque()
    queue.append((root, 1))
    while queue:
        current, depth = queue.popleft()
        if not current.is_dir():
            continue
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for p in entries:
            if p.is_file():
                if p.suffix.lower() in allowed_exts:
                    result.append(str(p.resolve()))
            elif p.is_dir():
                if depth < folder_depth:
                    queue.append((p, depth + 1))
    return sorted(result)


class SaveEvent(StrEnum):
    """Save lifecycle event type for list-level save iteration."""

    SAVING = 'saving'
    SAVED = 'saved'
    CANCELLED = 'cancelled'


class PathKind(StrEnum):
    """Supported input path kinds for file discovery/loading."""

    FILE = 'file'
    FOLDER = 'folder'
    CSV = 'csv'


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


@dataclass(frozen=True, slots=True)
class LoadWarning:
    """Non-fatal warning collected during safe loading."""

    message: str
    path: str | None = None
    row_index: int | None = None


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Result payload for safe load operations."""

    acq_image_list: AcqImageList
    warnings: tuple[LoadWarning, ...]


class LoadCancelled(RuntimeError):
    """Raised when a cooperative load operation is cancelled."""


class AcqImageList:
    """Backend-facing ordered collection of acquisition files."""

    def __init__(
        self,
        path: str,
        *,
        file_factory: Callable[[str], AcqImage] | None = None,
        folder_depth: int = 4,
        path_kind: PathKind | str | None = None,
    ):
        """Load one file or discover files under a directory.

        Args:
            path: Filesystem path to one file or directory.
            file_factory: Optional factory for creating file objects. Defaults to
                ``AcqImage``.
            folder_depth: When ``path`` is a directory, maximum directory depth to
                search (>= 1). Depth ``1`` is only the given folder; each increment
                includes one more level of child directories. Ignored when ``path`` is
                a file.
            path_kind: Optional explicit source type (`file`, `folder`, `csv`).
                When omitted, the constructor infers kind from path suffix and
                filesystem checks.
        """
        self.path = str(path)
        if folder_depth < 1:
            raise ValueError(f'folder_depth must be >= 1, got {folder_depth}')

        detected_kind: PathKind | str | None = path_kind
        if detected_kind is None:
            path_obj = Path(path)
            if path_obj.suffix.lower() == '.csv':
                detected_kind = PathKind.CSV
            elif os.path.isdir(path):
                detected_kind = PathKind.FOLDER
            else:
                detected_kind = PathKind.FILE

        if detected_kind == PathKind.FOLDER:
            self.file_list = _build_file_list(path, get_allowed_import_extensions(), folder_depth=folder_depth)
        elif detected_kind == PathKind.CSV:
            self.file_list = self._build_file_list_from_csv(path)
        else:
            self.file_list = [str(Path(path).resolve())]

        if file_factory is None:
            from acqstore.acq_image.acq_image import AcqImage

            file_factory = AcqImage
        self._files = [file_factory(file_path) for file_path in self.file_list]
        self._files_by_id = {acq_file.file_id: acq_file for acq_file in self._files}

    @classmethod
    def load_safe(
        cls,
        path: str,
        *,
        kind: PathKind | str,
        file_factory: Callable[[str], AcqImage] | None = None,
        folder_depth: int = 4,
        progress_callback: Callable[[int, int, str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> LoadResult:
        """Safely load acquisition files for file/folder/csv without raising.

        Args:
            path: Input path supplied by user or caller.
            kind: Explicit source kind (`file`, `folder`, or `csv`).
            file_factory: Optional file-construction callback for tests/injection.
            folder_depth: Maximum folder traversal depth for folder loads.
            progress_callback: Optional callback called as
                ``progress_callback(completed, total, message)`` after file
                discovery and after each successfully attempted file load.
            should_cancel: Optional callback checked between file loads. Return
                True to cancel loading.

        Returns:
            Structured result with loaded list and non-fatal warnings.

        Raises:
            LoadCancelled: If ``should_cancel`` requests cancellation.
        """
        warnings: list[LoadWarning] = []
        path_obj = Path(path).expanduser()
        base_path = str(path_obj.resolve(strict=False))
        if isinstance(kind, str):
            try:
                kind = PathKind(kind)
            except ValueError:
                warnings.append(LoadWarning(message=f'Unsupported load kind: {kind}', path=base_path))
                obj = cls.__new__(cls)
                obj.path = base_path
                obj.file_list = []
                obj._files = []
                obj._files_by_id = {}
                return LoadResult(acq_image_list=obj, warnings=tuple(warnings))

        candidate_paths: list[str] = []
        if kind == PathKind.FOLDER:
            if not path_obj.exists() or not path_obj.is_dir():
                warnings.append(LoadWarning(message='Folder does not exist or is not a directory', path=base_path))
            else:
                candidate_paths = _build_file_list(path_obj, get_allowed_import_extensions(), folder_depth=folder_depth)
        elif kind == PathKind.FILE:
            if not path_obj.exists() or not path_obj.is_file():
                warnings.append(LoadWarning(message='File does not exist or is not a file', path=base_path))
            else:
                candidate_paths = [str(path_obj.resolve())]
        elif kind == PathKind.CSV:
            csv_paths, csv_warnings = cls._build_file_list_from_csv_safe(path_obj)
            candidate_paths = csv_paths
            warnings.extend(csv_warnings)
        else:
            warnings.append(LoadWarning(message=f'Unsupported load kind: {kind}', path=base_path))

        files: list[AcqImage] = []
        total = len(candidate_paths)
        if progress_callback is not None:
            progress_callback(0, total, f'Discovered {total} file(s)')
        for candidate in candidate_paths:
            if should_cancel is not None and should_cancel():
                raise LoadCancelled('Load cancelled')
            try:
                if file_factory is None:
                    from acqstore.acq_image.acq_image import AcqImage

                    built = AcqImage(candidate)
                else:
                    built = file_factory(candidate)
                files.append(built)
            except Exception as exc:
                warnings.append(LoadWarning(message=f'Failed to load file: {exc}', path=str(Path(candidate).resolve(strict=False))))
            if progress_callback is not None:
                progress_callback(len(files), total, f'Loaded {len(files)}/{total}')

        obj = cls.__new__(cls)
        obj.path = base_path
        obj.file_list = [file.file_id for file in files]
        obj._files = files
        obj._files_by_id = {acq_file.file_id: acq_file for acq_file in files}
        return LoadResult(acq_image_list=obj, warnings=tuple(warnings))

    @staticmethod
    def _build_file_list_from_csv_safe(csv_path: Path) -> tuple[list[str], list[LoadWarning]]:
        """Parse CSV ``rel_path`` rows with per-row warnings."""
        warnings: list[LoadWarning] = []
        result: list[str] = []
        if not csv_path.exists() or not csv_path.is_file():
            return ([], [LoadWarning(message='CSV file does not exist', path=str(csv_path.resolve(strict=False)))])

        csv_parent = csv_path.parent.resolve(strict=False)
        try:
            with csv_path.open('r', encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None or 'rel_path' not in reader.fieldnames:
                    warnings.append(
                        LoadWarning(
                            message='CSV is missing required column "rel_path"',
                            path=str(csv_path.resolve(strict=False)),
                        )
                    )
                    return ([], warnings)
                for index, row in enumerate(reader, start=2):
                    raw_value = row.get('rel_path')
                    if raw_value is None or not str(raw_value).strip():
                        warnings.append(
                            LoadWarning(
                                message='CSV row has blank rel_path',
                                path=str(csv_path.resolve(strict=False)),
                                row_index=index,
                            )
                        )
                        continue
                    rel_value = str(raw_value).strip()
                    candidate = (csv_parent / rel_value).resolve(strict=False)
                    if not candidate.exists() or not candidate.is_file():
                        warnings.append(
                            LoadWarning(
                                message='CSV rel_path target does not exist',
                                path=str(candidate),
                                row_index=index,
                            )
                        )
                        continue
                    result.append(str(candidate))
        except Exception as exc:
            warnings.append(LoadWarning(message=f'Failed to parse CSV: {exc}', path=str(csv_path.resolve(strict=False))))
            return ([], warnings)

        unique: list[str] = []
        seen: set[str] = set()
        for item in result:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
        return (unique, warnings)

    def _build_file_list_from_csv(self, path: str | Path) -> list[str]:
        """Strict CSV parser used by constructor path-kind csv mode."""
        paths, warnings = self._build_file_list_from_csv_safe(Path(path))
        if warnings:
            first = warnings[0]
            raise ValueError(first.message)
        return paths

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
