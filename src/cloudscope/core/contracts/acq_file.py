"""Root acquisition-file contract for CloudScope."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .analysis import AcqAnalysisProtocol
from .metadata import AcqMetadataProtocol
from .images import AcqImagesProtocol
from .rois import AcqRoisProtocol


class AcqFileProtocol(Protocol):
    """Backend-facing root object for one acquisition file.

    The root file object exposes stable identity, persistence state, and a small
    set of helper objects that own image, ROI, metadata, and analysis concerns.
    """

    @property
    def file_id(self) -> str:
        """Return a stable identifier for this file."""

    @property
    def name(self) -> str:
        """Return a human-readable display name for this file."""

    @property
    def path(self) -> str | None:
        """Return the backing filesystem path when available.

        Returns:
            Full backing path for files loaded from persistent storage, or
            ``None`` for pathless sources such as in-memory uploads.
        """

    @property
    def is_dirty(self) -> bool:
        """Return whether this file has unsaved changes."""

    def save(self) -> None:
        """Persist pending changes for this file."""

    @property
    def images(self) -> AcqImagesProtocol:
        """Return image access helper for this file."""

    @property
    def rois(self) -> AcqRoisProtocol:
        """Return ROI helper for this file."""

    @property
    def analysis(self) -> AcqAnalysisProtocol:
        """Return analysis helper for this file."""

    @property
    def metadata_sections(self) -> Mapping[str, AcqMetadataProtocol]:
        """Return named metadata sections for this file.

        Returns:
            Mapping from stable section key to metadata helper.

        Notes:
            This mapping supports multiple metadata domains such as acquisition
            metadata and experimental metadata while keeping each section's API
            small and coherent.
        """

    def get_table_row(self) -> Mapping[str, Any]:
        """Return one semantic table row for file-list display.

        Returns:
            Mapping from stable column name to rendered or renderable value.
        """
