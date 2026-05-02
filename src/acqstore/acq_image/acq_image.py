from pathlib import Path
import json

from acqstore.schema import ACQ_FILE_LIST_SCHEMA, SchemaDefinition, validate_values_for_schema
from acqstore.utils.logging import get_logger
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
from .acq_analysis_set import AcqAnalysisSet

logger = get_logger(__name__)

_ACQIMAGE_SIDECAR_VERSION = 2
_ACQIMAGE_SIDECAR_REQUIRED_KEYS = {
    'version',
    'accepted',
    'rois',
    'experiment_metadata',
    'image_header_metadata',
    'analysis',  # [dict], one dict per item in analysis set
}


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
        self._acq_analysis_set = AcqAnalysisSet(self.path)
        
        self.load_sidecar_json()

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
        return (
            self._rois.is_dirty()
            or self._acq_analysis_set.is_dirty()
            or any(section.is_dirty() for section in self.get_metadata_sections())
        )

    def save(self) -> None:
        """Persist pending changes for this file."""
        
        # save one json file for each acq image
        self.save_sidecar_json()

        # save the analysis results to csv files (one file per analysis type)
        self._acq_analysis_set.save_results_df(self.path)

        # set dirty flags to false
        self._rois.set_clean()
        self._acq_analysis_set.set_clean()
        for section in self.get_metadata_sections():
            section.set_clean()

    def get_sidecar_json_path(self) -> str:
        """Return sidecar JSON path for this acquisition file.

        Returns:
            Sidecar path using full acquisition filename with extension plus
            ``.json`` suffix (for example, ``image.tif.json``).
        """
        return str(Path(f'{self.path}.json'))

    def _build_sidecar_payload(self) -> dict[str, object]:
        """Build sidecar JSON payload for this acquisition file.

        Returns:
            JSON-serializable sidecar payload.
        """
        return {
            'version': _ACQIMAGE_SIDECAR_VERSION,
            'accepted': bool(self._accept),
            'rois': self._rois.to_list(),
            'experiment_metadata': self._experimental_metadata.to_dict(),
            # Saved for forward compatibility; not hydrated in phase 1 load path.
            'image_header_metadata': self._image_header_metadata.get_values(),
            
            'analysis': self._acq_analysis_set.serialize_json_analysis(),
        }

    def _apply_loaded_sidecar_payload(self, payload: dict[str, object]) -> None:
        """Apply validated sidecar payload to runtime state.

        Args:
            payload: Parsed and validated sidecar payload.
        """
        rois_obj = payload['rois']
        if not isinstance(rois_obj, list):
            raise ValueError("Sidecar field 'rois' must be a list")
        if any(not isinstance(item, dict) for item in rois_obj):
            raise ValueError("Sidecar field 'rois' must contain dict entries")

        exp_obj = payload['experiment_metadata']
        if exp_obj is not None and not isinstance(exp_obj, dict):
            raise ValueError("Sidecar field 'experiment_metadata' must be an object")

        self._accept = bool(payload['accepted'])
        self._rois.from_list(rois_obj)
        self._experimental_metadata = ExperimentMetadata.from_dict(exp_obj)
        # Phase 1 behavior: do not hydrate image header metadata from JSON.

        analysis_obj = payload['analysis']
        if not isinstance(analysis_obj, list):
            raise ValueError("Sidecar field 'analysis' must be a list")
        self._acq_analysis_set.load_json_analysis(analysis_obj)
        self._acq_analysis_set.load_all_results_dfs_from_csv(self.path)

    def save_sidecar_json(self) -> None:
        """Persist sidecar JSON for this acquisition file."""
        sidecar_path = Path(self.get_sidecar_json_path())
        payload = self._build_sidecar_payload()
        sidecar_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding='utf-8',
        )

    def load_sidecar_json(self) -> None:
        """Load sidecar JSON into runtime state when present.

        Invalid sidecar content is ignored with a warning.
        """
        sidecar_path = Path(self.get_sidecar_json_path())
        if not sidecar_path.is_file():
            return

        try:
            raw = json.loads(sidecar_path.read_text(encoding='utf-8'))
            if not isinstance(raw, dict):
                raise ValueError('Sidecar JSON payload must be an object')

            missing = sorted(_ACQIMAGE_SIDECAR_REQUIRED_KEYS - set(raw.keys()))
            if missing:
                raise ValueError(f'Sidecar JSON missing required keys: {missing}')

            extra = sorted(set(raw.keys()) - _ACQIMAGE_SIDECAR_REQUIRED_KEYS)
            if extra:
                logger.warning('Ignoring unknown AcqImage sidecar keys for %s: %s', self.path, extra)

            version = raw['version']
            if version != _ACQIMAGE_SIDECAR_VERSION:
                raise ValueError(
                    f'Unsupported AcqImage sidecar version {version!r}; '
                    f'expected {_ACQIMAGE_SIDECAR_VERSION!r}'
                )

            self._apply_loaded_sidecar_payload(raw)
        except Exception as exc:  # pragma: no cover - validated in tests
            logger.warning('Failed to load sidecar JSON for %s: %s', self.path, exc)

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
    def analysis_set(self) -> AcqAnalysisSet:
        """Return analysis helper for this file."""
        return self._acq_analysis_set
    
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