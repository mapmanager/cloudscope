from pathlib import Path

from acqstore.schema import ACQ_FILE_LIST_SCHEMA, SchemaDefinition, validate_values_for_schema
from .metadata import ExperimentMetadata
from .roi import ImageBounds, RoiSet
from .file_loaders.base_file_loader import BaseFileLoader
from .file_loaders.file_loader_factory import create_file_loader
from .supported_import_extensions import (
    DEFAULT_IMPORT_EXTENSIONS,
    add_allowed_import_extension,
    get_allowed_import_extensions,
    remove_allowed_import_extension,
    reset_allowed_import_extensions,
    set_allowed_import_extensions,
)
from .acq_analysis import AcqAnalysis

__all__ = [
    'DEFAULT_IMPORT_EXTENSIONS',
    'get_allowed_import_extensions',
    'set_allowed_import_extensions',
    'add_allowed_import_extension',
    'remove_allowed_import_extension',
    'reset_allowed_import_extensions',
    'AcqImage',
]

class AcqImage:
    """Backend-facing root object for one acquisition file."""

    def __init__(self, path: str):
        """Create a new acquisition file wrapper.

        Args:
            path: Filesystem path for this acquisition file.

        Raises:
            ValueError: If the file extension is not a supported acquisition format.
        """
        self.path = str(Path(path).resolve())

        self._images = create_file_loader(self.path)
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
    def experimental_metadata(self) -> ExperimentMetadata:
        """Return user-editable experiment metadata for this file."""
        return self._experimental_metadata

    def get_metadata_sections(self) -> tuple[ExperimentMetadata, ...]:
        """Return metadata section objects exposed for schema-driven UIs."""
        return (self._experimental_metadata,)

    @property
    # def analysis(self) -> list["AcqAnalysis"]:
    def analysis(self) -> AcqAnalysis:
        """Return analysis helper for this file."""
        return self.acq_analysis
    
    def get_schema(self) -> SchemaDefinition:
        """Return the semantic schema for this acquisition file row."""
        return ACQ_FILE_LIST_SCHEMA

    def get_schema_row(self) -> dict[str, object]:
        """Return schema-keyed values for this acquisition file.

        Returns:
            Mapping from schema field names to backend values.

        Raises:
            KeyError: If required schema fields are missing.
            ValueError: If values include keys outside the schema.
        """
        values: dict[str, object] = {
            'name': self.name,
            'path': self.path,
            'num_channels': self.images.num_channels,
            'num_rois': self.rois.num_rois,
        }
        validate_values_for_schema(self.get_schema(), values)
        return values

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