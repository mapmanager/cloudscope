from typing import Any, Literal

from .metadata import ExperimentMetadata
from .roi import RoiSet
from .file_loaders.base_file_loader import BaseFileLoader
from .acq_analysis import AcqAnalysis

"""Supported acquisition file types."""
AllowedImportExtension = Literal["tif", "oir"]
ALLOWED_IMPORT_EXTENSIONS: tuple[AllowedImportExtension, ...] = ("tif", "oir")

class AcqImage:
    def __init__(self, path:str):
        self.path = path

        self._images = BaseFileLoader(path)
        self._experimental_metadata = ExperimentMetadata()
        self._rois = RoiSet()
        self.acq_analysis = AcqAnalysis()

    @property
    def file_id(self) -> str:
        """Return a stable identifier for this file."""
        return self.path

    @property
    def name(self) -> str:
        """Return a human-readable display name for this file."""
        return self.path

    @property
    def is_dirty(self) -> bool:
        """Return whether this file has unsaved changes."""
        return False

    def save(self) -> None:
        """Persist pending changes for this file."""
        pass

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
        return {
            'path': self.path,
            'num_channels': self._images.num_channels,
            'num_rois': self._rois.num_rois,
            # 'experimental_metadata': self._experimental_metadata.get_table_row(),
            # 'analysis': self._analysis.get_table_row(),
        }