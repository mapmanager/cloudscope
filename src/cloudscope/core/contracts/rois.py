"""ROI collection contract for one acquisition file."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol

from acqstore.acq_image.roi import (
    BaseROI,
    LineEndpoints,
    LineROI,
    RectROI,
    RectRoiBounds,
)


class AcqRoisProtocol(Protocol):
    """Backend-facing ROI collection and CRUD surface for one file."""

    def is_dirty(self) -> bool:
        """Return whether the ROI collection has unsaved changes.

        Returns:
            True if the ROI collection has unsaved changes.
        """
        ...

    def set_clean(self) -> None:
        """Mark the ROI collection as clean.

        Returns:
            None.
        """
        ...

    def create_rect_roi(
        self,
        bounds: RectRoiBounds | None = None,
        name: str = "",
        note: str = "",
    ) -> RectROI:
        """Create and return a rectangular ROI.

        Args:
            bounds: Optional rectangular bounds. If None, the implementation
                may use its default creation behavior.
            name: Human-readable ROI name.
            note: Optional human-readable ROI note.

        Returns:
            Newly created rectangular ROI.
        """
        ...

    def create_line_roi(
        self,
        endpoints: LineEndpoints,
        name: str = "",
        note: str = "",
    ) -> LineROI:
        """Create and return a line-segment ROI.

        Args:
            endpoints: Line endpoints.
            name: Human-readable ROI name.
            note: Optional human-readable ROI note.

        Returns:
            Newly created line-segment ROI.
        """
        ...

    def edit_rect_roi(
        self,
        roi_id: int,
        *,
        bounds: RectRoiBounds | None = None,
        name: str | None = None,
        note: str | None = None,
    ) -> RectROI:
        """Edit and return an existing rectangular ROI.

        Args:
            roi_id: ROI identifier.
            bounds: New rectangular bounds, or None to leave unchanged.
            name: New name, or None to leave unchanged.
            note: New note, or None to leave unchanged.

        Returns:
            Edited rectangular ROI.
        """
        ...

    def edit_line_roi(
        self,
        roi_id: int,
        *,
        endpoints: LineEndpoints | None = None,
        name: str | None = None,
        note: str | None = None,
    ) -> LineROI:
        """Edit and return an existing line-segment ROI.

        Args:
            roi_id: ROI identifier.
            endpoints: New endpoints, or None to leave unchanged.
            name: New name, or None to leave unchanged.
            note: New note, or None to leave unchanged.

        Returns:
            Edited line-segment ROI.
        """
        ...

    def delete(self, roi_id: int) -> None:
        """Delete a ROI by identifier.

        Args:
            roi_id: ROI identifier.

        Returns:
            None.
        """
        ...

    def clear(self) -> int:
        """Delete all ROIs.

        Returns:
            Number of deleted ROIs.
        """
        ...

    def get(self, roi_id: int) -> BaseROI | None:
        """Return a ROI by identifier.

        Args:
            roi_id: ROI identifier.

        Returns:
            ROI instance or None.
        """
        ...

    def get_roi_ids(self) -> list[int]:
        """Return ROI identifiers in creation order.

        Returns:
            ROI identifiers.
        """
        ...

    def num_rois(self) -> int:
        """Return number of ROIs.

        Returns:
            Number of ROIs.
        """
        ...

    def as_list(self) -> list[BaseROI]:
        """Return ROIs in creation order.

        Returns:
            ROI instances.
        """
        ...

    def to_list(self) -> list[dict[str, Any]]:
        """Serialize all ROIs.

        Returns:
            Serialized ROI dictionaries.
        """
        ...

    def from_list(self, data: list[dict[str, Any]]) -> AcqRoisProtocol:
        """Replace ROI collection from serialized ROI dictionaries.

        Args:
            data: Serialized ROI dictionaries.

        Returns:
            This ROI collection.
        """
        ...

    def __iter__(self) -> Iterator[BaseROI]:
        """Iterate over ROIs in creation order.

        Returns:
            Iterator over ROI instances.
        """
        ...