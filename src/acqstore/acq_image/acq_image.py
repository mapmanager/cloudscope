from pathlib import Path
from typing import Any, Literal

from .metadata import ExperimentMetadata
from .roi import ImageBounds, RoiSet
from .file_loaders.base_file_loader import BaseFileLoader
from .acq_analysis import AcqAnalysis

"""Supported acquisition file types."""
AllowedImportExtension = Literal["tif", "oir"]
ALLOWED_IMPORT_EXTENSIONS: tuple[AllowedImportExtension, ...] = ("tif", "oir")

class AcqImage:
    """Backend-facing root object for one acquisition file."""

    def __init__(self, path: str):
        """Create a new acquisition file wrapper.

        Args:
            path: Filesystem path for this acquisition file.
        """
        self.path = str(Path(path).resolve())

        self._images = BaseFileLoader(path)
        self._experimental_metadata = ExperimentMetadata()
        self._rois = RoiSet(self._infer_image_bounds())
        self.acq_analysis = AcqAnalysis()

    @property
    def file_id(self) -> str:
        """Return a stable identifier for this file."""
        return self.path

    @property
    def name(self) -> str:
        """Return a human-readable display name for this file."""
        return Path(self.path).name

    @property
    def is_dirty(self) -> bool:
        """Return whether this file has unsaved changes."""
        return self._rois.is_dirty()

    def save(self) -> None:
        """Persist pending changes for this file."""
        self._rois.set_clean()

    @property
    def images(self) -> BaseFileLoader:
        """Return image access helper for this file."""
        return self._images

    @property
    def rois(self) -> RoiSet:
        """Return ROI helper for this file."""
        return self._rois
    @property
    # def analysis(self) -> list["AcqAnalysis"]:
    def analysis(self) -> AcqAnalysis:
        """Return analysis helper for this file."""
        return self.acq_analysis
    
    def get_table_row(self) -> dict[str, Any]:
        """Return one semantic table row for file-list display."""
        return {
            'path': self.path,
            'num_channels': self._images.num_channels,
            'num_rois': self._rois.num_rois,
            # 'experimental_metadata': self._experimental_metadata.get_table_row(),
            # 'analysis': self._analysis.get_table_row(),
        }

    def get_default_channel(self) -> int | None:
        """Return the default channel index for this file.

        Returns:
            Zero-based channel index for the first channel, or ``None`` when the
            file exposes no channels.
        """
        return self._images.default_channel

    def get_default_roi(self) -> int | None:
        """Return the default ROI identifier for this file.

        Returns:
            First ROI identifier in creation order, or ``None`` when no ROI
            exists.
        """
        roi_ids = self._rois.get_roi_ids()
        return roi_ids[0] if roi_ids else None

    def _infer_image_bounds(self) -> ImageBounds:
        """Infer image bounds from loaded header information.

        Returns:
            Image bounds built from known header dimensions.
        """
        sizes = self._images.header.sizes
        width = int(sizes.get('X', 1))
        height = int(sizes.get('Y', 1))
        num_slices = int(sizes.get('Z', 1))
        return ImageBounds(width=width, height=height, num_slices=num_slices)