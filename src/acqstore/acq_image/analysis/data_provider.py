"""Analysis data-provider interfaces.

The concrete provider is intentionally thin. It delegates image/ROI/header
access to ``AcqImage`` so the analysis package does not duplicate ROI slicing
logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import numpy as np

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


class AnalysisDataProvider(Protocol):
    """Minimal data access surface needed by analyses."""

    def get_roi_image(self, channel: int, roi_id: int) -> np.ndarray:
        """Return image data for one channel cropped to one ROI.

        Args:
            channel: Channel index.
            roi_id: ROI identifier.

        Returns:
            Two-dimensional ROI image data.
        """
        ...

    def get_image_physical_units(self) -> tuple[float, float]:
        """Return physical units for the 2D image plane.

        Returns:
            Per-pixel ``(step_y, step_x)`` for ``(Y, X)`` image data.
        """
        ...


class AcqImageAnalysisDataProvider:
    """Analysis data provider backed by one AcqImage.

    Args:
        acq_image: Parent acquisition image.
    """

    def __init__(self, acq_image: AcqImage) -> None:
        self._acq_image = acq_image

    def get_roi_image(self, channel: int, roi_id: int) -> np.ndarray:
        """Return image data for one channel cropped to one ROI.

        Args:
            channel: Channel index.
            roi_id: ROI identifier.

        Returns:
            Two-dimensional ROI image data.
        """
        return self._acq_image.get_roi_image(channel=channel, roi_id=roi_id)

    def get_image_physical_units(self) -> tuple[float, float]:
        """Return physical units for the 2D image plane.

        Returns:
            Per-pixel ``(step_y, step_x)`` for ``(Y, X)`` image data.
        """
        return self._acq_image.get_image_physical_units()
