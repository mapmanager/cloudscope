"""Metadata contract types for CloudScope backends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from .common import MetadataFieldSchema


class AcqMetadataProtocol(Protocol):
    """Editable metadata section contract for one acquisition file.

    A file may expose multiple metadata sections. Each section carries both data
    and semantic schema so metadata-oriented views can remain thin.
    """

    @property
    def section_name(self) -> str:
        """Return the stable metadata section name."""

    def get_data(self) -> Mapping[str, Any]:
        """Return current metadata values for this section.

        Returns:
            Mapping from stable field name to current metadata value.
        """

    def get_schema(self) -> Sequence[MetadataFieldSchema]:
        """Return semantic field schema for this section.

        Returns:
            Ordered metadata field schema entries used by the GUI to construct
            editors, labels, grouping, and tooltips.
        """

    def update(self, patch: Mapping[str, Any]) -> None:
        """Apply a partial metadata update.

        Args:
            patch: Mapping of stable field name to replacement value.

        Raises:
            KeyError: If a field name in ``patch`` is not known.
            ValueError: If a proposed value fails backend validation.
        """
