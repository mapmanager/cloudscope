from pathlib import Path

from acqstore.schema import ACQ_FILE_LIST_SCHEMA, SchemaDefinition, validate_values_for_schema
from .file_loaders.base_file_loader import BaseFileLoader, ImageHeader
from .metadata import ExperimentMetadata, ImageHeaderMetadata
from .roi import ImageBounds, RoiSet
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


def parent_grandparent_folder_names(
    file_path: str,
    *,
    loaded_from_stream: bool,
) -> tuple[str, str]:
    """Return ``(parent_folder_name, grandparent_folder_name)`` for a file path.

    Used for file-list schema fields derived from the acquisition path. Returns
    ``(\"\", \"\")`` when there is no reliable filesystem layout (stream upload,
    unresolvable path, missing parent directory, or I/O errors while checking).

    Args:
        file_path: Path to the acquisition file (typically absolute and resolved).
        loaded_from_stream: When true, the acquisition is not tied to a real
            on-disk file path (e.g. loader opened from a stream); names are empty.

    Returns:
        Two strings suitable for schema ``parent`` / ``grandparent`` (each may be
        empty). Names are :attr:`pathlib.Path.name` of the parent and grandparent
        directories when those directories exist.
    """
    if loaded_from_stream:
        return '', ''
    raw = (file_path or '').strip()
    if not raw:
        return '', ''
    try:
        p = Path(raw).expanduser()
        p = p.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return '', ''

    parent = p.parent
    if not str(parent) or parent == p:
        return '', ''
    try:
        if not parent.is_dir():
            return '', ''
    except OSError:
        return '', ''

    parent_name = parent.name or ''

    gp = parent.parent
    grandparent_name = ''
    if str(gp) and gp != parent:
        try:
            if gp.is_dir():
                grandparent_name = gp.name or ''
        except OSError:
            grandparent_name = ''

    return parent_name, grandparent_name


__all__ = [
    'DEFAULT_IMPORT_EXTENSIONS',
    'get_allowed_import_extensions',
    'set_allowed_import_extensions',
    'add_allowed_import_extension',
    'remove_allowed_import_extension',
    'reset_allowed_import_extensions',
    'AcqImage',
    'parent_grandparent_folder_names',
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

        self._accept = True

        self._images = create_file_loader(self.path)
        self._experimental_metadata = ExperimentMetadata()
        self._image_header_metadata = ImageHeaderMetadata(self._images.header, self._apply_image_header)
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
        return self._rois.is_dirty() or any(section.is_dirty() for section in self.get_metadata_sections())

    def save(self) -> None:
        """Persist pending changes for this file."""
        self._rois.set_clean()
        for section in self.get_metadata_sections():
            section.set_clean()

    @property
    def images(self) -> BaseFileLoader:
        """Return image access helper for this file."""
        return self._images

    @property
    def rois(self) -> RoiSet:
        """Return ROI helper for this file."""
        return self._rois

    def get_metadata_sections(self) -> tuple[ExperimentMetadata | ImageHeaderMetadata, ...]:
        """Return metadata section objects exposed for schema-driven UIs."""
        return (self._experimental_metadata, self._image_header_metadata)

    def get_metadata_section(self, metadata_section_id: str) -> ExperimentMetadata | ImageHeaderMetadata:
        """Return one metadata section by identifier.

        Raises:
            ValueError: If section id is unknown.
        """
        for section in self.get_metadata_sections():
            sid = getattr(section, 'metadata_section_id', None)
            if sid == metadata_section_id:
                return section
        raise ValueError(f'Unknown metadata section_id: {metadata_section_id!r}')

    def apply_metadata_patch(self, metadata_section_id: str, patch: dict[str, object]) -> None:
        """Apply metadata patch to a known section.

        Args:
            metadata_section_id: Metadata section discriminator string.
            patch: Field patch for that section.

        Raises:
            ValueError: If ``metadata_section_id`` is unknown.
        """
        section = self.get_metadata_section(metadata_section_id)
        section.update_values(dict(patch))

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
        loaded_from_stream = getattr(self._images, '_stream', None) is not None
        parent, grandparent = parent_grandparent_folder_names(
            self.path,
            loaded_from_stream=loaded_from_stream,
        )
        values: dict[str, object] = {
            'name': self.name,
            'path': self.path,
            'parent': parent,
            'grandparent': grandparent,
            'genotype': self._experimental_metadata.genotype,
            'num_channels': self.images.num_channels,
            'num_rois': self.rois.num_rois,
            'accept': self._accept,
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

    def _apply_image_header(self, header: ImageHeader) -> None:
        """Apply updated header to backing loader."""
        self._images.replace_header(header)