"""Acquisition-file object for images, metadata, ROIs, and analysis results.

``AcqImage`` is the central per-file object in ``acqstore``. It wraps one
acquisition file, exposes image data through the file-loader API, owns
experiment/image-header metadata, owns the ROI set, and owns the analysis set
for that file. CloudScope GUI views, scripts, and notebooks all use this same
object so analysis behavior does not depend on whether work is done in the GUI
or in Python code.

This module is intended for public scripting use. The most common entry points
are ``AcqImage`` for one file and ``AcqImageList`` for collections of files.
"""

from pathlib import Path
import json

import numpy as np

from acqstore.schema import ACQ_FILE_LIST_SCHEMA, SchemaDefinition, validate_values_for_schema
from acqstore.utils.logging import get_logger
from .acq_pixels import AcqPixels
from .file_loaders.base_file_loader import BaseFileLoader, ImageHeader
from .ome_zarr_io import read_json_file, write_json_file
from .metadata import ExperimentMetadata, ImageHeaderMetadata
from .roi import ImageBounds, LineROI, RectROI, RoiSet
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
from .analysis.data_provider import AcqImageAnalysisDataProvider
from .image_contrast import ImageContrast, contrast_clip_min_max
from .tree_rows import (
    ACQ_TREE_ANALYSIS_CHANNEL_FIELD,
    ACQ_TREE_ANALYSIS_NAME_FIELD,
    ACQ_TREE_ANALYSIS_ROI_ID_FIELD,
    ACQ_TREE_PATH_FIELD,
    ACQ_TREE_ROW_ID_FIELD,
    ACQ_TREE_ROW_TYPE_ANALYSIS,
    ACQ_TREE_ROW_TYPE_FIELD,
    ACQ_TREE_ROW_TYPE_FILE,
    build_analysis_tree_row_id,
)

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
# Keys that may appear in the sidecar without being required. They are tolerated
# on load (no "unknown key" warning) and written on save when present.
# To disable image_contrast persistence entirely, comment out 'image_contrast'
# below and the region-marked blocks in _build_sidecar_payload and
# _apply_loaded_sidecar_payload; the in-memory defaults flow continues to work.
_ACQIMAGE_SIDECAR_OPTIONAL_KEYS = {'image_contrast'}


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
    """Root object for one acquisition file.

    An ``AcqImage`` represents one loaded acquisition file and its sidecar state.
    It owns the file loader, metadata sections, ROI set, image-contrast state,
    and ``AcqAnalysisSet`` for this file. The object is used directly by
    CloudScope and is also the preferred starting point for scripts that need to
    load one file, crop image data by ROI, run analysis, or save results.

    The constructor loads image-header information from the source file and then
    attempts to hydrate persisted sidecar state from ``<source-file>.json`` when
    that file exists. Calling :meth:`save` writes the sidecar JSON and analysis
    CSV files next to the source file.

    Array conventions:
        Two-dimensional image arrays use ``(Y, X)`` order, which corresponds to
        ``(rows, columns)``. For line-scan kymographs, CloudScope interprets
        ``Y`` as time/line index and ``X`` as distance along the sampled line.
        ROI bounds use the same row/column coordinate system.

    Examples:
        Load a file, access the default channel, crop the first ROI, and inspect
        physical pixel spacing::

            from acqstore.acq_image import AcqImage

            acq = AcqImage("example.tif")
            channel = acq.get_default_channel()
            roi_id = acq.get_default_roi()
            if channel is not None and roi_id is not None:
                roi_image = acq.get_roi_image(channel, roi_id)
                step_y, step_x = acq.get_image_physical_units()

    Args:
        path: Filesystem path for one supported acquisition file.

    Raises:
        ValueError: If the file extension is not a supported acquisition format.
    """

    def __init__(self, path: str):
        """Create and hydrate an acquisition file object.

        The source file is opened through the appropriate file loader, default
        metadata/ROI/analysis containers are created, and sidecar JSON is loaded
        when present. The constructor does not run analysis.

        Args:
            path: Filesystem path for this acquisition file.

        Raises:
            ValueError: If the file extension is not a supported acquisition format.
        """
        self.path = str(Path(path).resolve())

        self._accept = True

        self._images = create_file_loader(self.path)
        self._pixels = self._images.load_pixels()
        self._experimental_metadata = ExperimentMetadata()
        self._image_header_metadata = ImageHeaderMetadata(self._pixels.header, self._apply_image_header)
        self._rois = RoiSet(self._infer_image_bounds())
        self._acq_analysis_set = AcqAnalysisSet(
            self.path,
            data_provider=AcqImageAnalysisDataProvider(self),
        )
        self._image_contrasts: dict[int, ImageContrast] = {}
        self._image_contrast_dirty = False

        if self.path.lower().endswith('.cs.ome.zarr'):
            self.load_native_zarr_sidecar_json()
        else:
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
            or getattr(self, '_image_contrast_dirty', False)
            or any(section.is_dirty() for section in self.get_metadata_sections())
        )

    def save(self) -> None:
        """Persist metadata, ROIs, contrast state, and analysis results.

        ``save`` writes the JSON sidecar for this acquisition and asks the
        analysis set to write CSV result files. It then marks metadata sections,
        ROI state, contrast state, and analysis state as clean.

        Notes:
            Source image pixels are not modified. Analysis CSV files are written
            by analysis type, while per-file state is stored in the sidecar JSON.
        """
        
        # save one json file for each acq image
        self.save_sidecar_json()

        # save the analysis results to csv files (one file per analysis type)
        self._acq_analysis_set.save_results_df(self.path)

        # set dirty flags to false
        self._mark_clean_after_save()

    def save_native_zarr(self, path: str | Path, *, overwrite: bool = False) -> None:
        """Persist this acquisition as one acqstore-native OME-Zarr store.

        The image portion is written as an OME-NGFF/OME-Zarr-compatible group.
        CloudScope/acqstore-specific state is embedded under ``acqstore/`` so
        standards-aware tools can ignore it while acqstore can round-trip it.
        Existing :meth:`save` sidecar behavior is intentionally unchanged.

        Args:
            path: Destination store path, typically ending in ``.cs.ome.zarr``.
            overwrite: Whether to replace an existing destination store.
        """
        dest = Path(path)
        self._pixels.to_ome_zarr(dest, overwrite=overwrite)
        write_json_file(dest / 'acqstore' / 'acq_image.json', self._build_sidecar_payload())
        self._acq_analysis_set.save_results_tables_to_directory(dest / 'acqstore' / 'analysis')
        write_json_file(
            dest / 'acqstore' / 'manifest.json',
            {
                'format': 'acqstore-native-ome-zarr',
                'version': 1,
                'image_group': '.',
                'sidecar': 'acqstore/acq_image.json',
            },
        )
        self._mark_clean_after_save()

    def _mark_clean_after_save(self) -> None:
        """Clear dirty flags after a successful save."""
        self._rois.set_clean()
        self._acq_analysis_set.set_clean()
        self._image_contrast_dirty = False
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
        payload: dict[str, object] = {
            'version': _ACQIMAGE_SIDECAR_VERSION,
            'accepted': bool(self._accept),
            'rois': self._rois.to_list(),
            'experiment_metadata': self._experimental_metadata.to_dict(),
            # Saved for forward compatibility; not hydrated in phase 1 load path.
            'image_header_metadata': self._image_header_metadata.get_values(),

            'analysis': self._acq_analysis_set.serialize_json_analysis(),
        }
        # region image_contrast persistence
        # Comment out this region (and the matching one in
        # _apply_loaded_sidecar_payload) to disable image_contrast persistence;
        # in-memory defaults seeded by PrimaryPlaneLoaded continue to work.
        payload['image_contrast'] = self._serialize_image_contrast_for_sidecar()
        # endregion image_contrast persistence
        return payload

    def _serialize_image_contrast_for_sidecar(self) -> dict[str, dict[str, object]]:
        """Return ``{str(channel): {...}}`` for the current ``_image_contrasts``.

        Returns:
            JSON-serializable mapping from stringified channel index to contrast
            fields. Empty dict when no entries exist (keeps file format predictable).
        """
        out: dict[str, dict[str, object]] = {}
        for channel, contrast in sorted(self._image_contrasts.items()):
            out[str(int(channel))] = {
                'color_lut': str(contrast.color_lut),
                'value_min': int(contrast.value_min),
                'value_max': int(contrast.value_max),
                'img_min': int(contrast.img_min),
                'img_max': int(contrast.img_max),
            }
        return out

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

        # region image_contrast persistence
        # Comment out this region (and the matching one in
        # _build_sidecar_payload) to disable image_contrast persistence;
        # in-memory defaults seeded by PrimaryPlaneLoaded continue to work.
        self._image_contrasts = self._parse_image_contrast_from_sidecar(
            payload.get('image_contrast', {})
        )
        self._image_contrast_dirty = False
        # endregion image_contrast persistence

    def _parse_image_contrast_from_sidecar(
        self,
        raw: object,
    ) -> dict[int, ImageContrast]:
        """Parse a sidecar ``image_contrast`` value into the in-memory dict.

        Args:
            raw: Value read from ``payload.get('image_contrast', {})``.

        Returns:
            Mapping from integer channel index to :class:`ImageContrast`.
            Returns an empty dict (with a warning) when the payload is malformed
            so a broken sidecar entry never blocks loading other state.
        """
        if not isinstance(raw, dict):
            logger.warning(
                "Sidecar field 'image_contrast' must be an object for %s; ignoring",
                self.path,
            )
            return {}
        result: dict[int, ImageContrast] = {}
        for key, value in raw.items():
            try:
                channel = int(str(key), 10)
            except (TypeError, ValueError):
                logger.warning(
                    "Skipping image_contrast entry with non-int channel key %r in %s",
                    key,
                    self.path,
                )
                continue
            if not isinstance(value, dict):
                logger.warning(
                    "Skipping image_contrast entry for channel %s in %s: value is not an object",
                    channel,
                    self.path,
                )
                continue
            try:
                result[channel] = ImageContrast(
                    color_lut=str(value['color_lut']),
                    value_min=int(value['value_min']),
                    value_max=int(value['value_max']),
                    img_min=int(value['img_min']),
                    img_max=int(value['img_max']),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed image_contrast entry for channel %s in %s: %s",
                    channel,
                    self.path,
                    exc,
                )
        return result

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
            self._load_sidecar_payload(
                json.loads(sidecar_path.read_text(encoding='utf-8')),
                source=str(sidecar_path),
            )
        except Exception as exc:  # pragma: no cover - validated in tests
            logger.warning('Failed to load sidecar JSON for %s: %s', self.path, exc)

    def load_native_zarr_sidecar_json(self) -> None:
        """Load embedded acqstore state from a native ``.cs.ome.zarr`` store."""
        sidecar_path = Path(self.path) / 'acqstore' / 'acq_image.json'
        if not sidecar_path.is_file():
            return
        try:
            self._load_sidecar_payload(read_json_file(sidecar_path), source=str(sidecar_path))
            self._acq_analysis_set.load_results_tables_from_directory(
                Path(self.path) / 'acqstore' / 'analysis'
            )
        except Exception as exc:  # pragma: no cover - defensive native-load path
            logger.warning('Failed to load native Zarr sidecar for %s: %s', self.path, exc)

    def _load_sidecar_payload(self, raw: object, *, source: str) -> None:
        """Validate and apply one sidecar payload from an external or embedded source."""
        if not isinstance(raw, dict):
            raise ValueError('Sidecar JSON payload must be an object')

        missing = sorted(_ACQIMAGE_SIDECAR_REQUIRED_KEYS - set(raw.keys()))
        if missing:
            raise ValueError(f'Sidecar JSON missing required keys: {missing}')

        extra = sorted(
            set(raw.keys())
            - _ACQIMAGE_SIDECAR_REQUIRED_KEYS
            - _ACQIMAGE_SIDECAR_OPTIONAL_KEYS
        )
        if extra:
            logger.warning('Ignoring unknown AcqImage sidecar keys for %s: %s', source, extra)

        version = raw['version']
        if version != _ACQIMAGE_SIDECAR_VERSION:
            raise ValueError(
                f'Unsupported AcqImage sidecar version {version!r}; '
                f'expected {_ACQIMAGE_SIDECAR_VERSION!r}'
            )

        self._apply_loaded_sidecar_payload(raw)

    @property
    def pixels(self) -> AcqPixels:
        """Return pixels plus OME/NGFF-style acquisition metadata for this file.

        The normal constructor initializes ``_pixels`` immediately. This lazy
        fallback keeps lightweight tests and scripts that construct ``AcqImage``
        instances without invoking ``__init__`` from failing when a real loader
        is present. Test doubles that only mimic legacy loader attributes should
        continue using ``images``-level fields such as ``num_channels``.
        """
        if not hasattr(self, '_pixels'):
            load_pixels = getattr(getattr(self, '_images', None), 'load_pixels', None)
            if not callable(load_pixels):
                raise AttributeError(
                    "AcqImage pixels are not initialized and the image loader "
                    "does not provide load_pixels()."
                )
            self._pixels = load_pixels()
        return self._pixels

    @property
    def images(self) -> BaseFileLoader:
        """Return the file-loader image access object.

        The loader owns source pixel access and image-header metadata. Scripts
        may use it for direct image access when they need full slices or loader
        details; analysis code should usually use :meth:`get_roi_image` through
        ``AnalysisDataProvider`` instead.
        """
        return self._images

    @property
    def rois(self) -> RoiSet:
        """Return the ROI set for this acquisition.

        ROIs are shared across channels for one ``AcqImage``. Rectangular ROI
        bounds use the same row/column coordinate system as ``(Y, X)`` image
        arrays. Mutating ROIs marks the file dirty and may invalidate analysis
        associated with the edited ROI.
        """
        return self._rois

    def get_image_contrast(self, channel: int) -> ImageContrast | None:
        """Return the current contrast state for one channel.

        Args:
            channel: Zero-based channel index.

        Returns:
            Stored :class:`ImageContrast` for ``channel``, or ``None`` when no
            entry exists (no plane has been provided yet).
        """
        return self._image_contrasts.get(int(channel))

    def set_image_contrast(self, channel: int, contrast: ImageContrast) -> None:
        """Set the contrast state for one channel and mark the file dirty.

        Args:
            channel: Zero-based channel index.
            contrast: New contrast snapshot. A copy is stored.
        """
        self._image_contrasts[int(channel)] = contrast.copy()
        self._image_contrast_dirty = True

    def ensure_image_contrast_from_plane(
        self,
        channel: int,
        plane: np.ndarray,
        *,
        default_color_lut: str,
        percentile_low: float,
        percentile_high: float,
    ) -> ImageContrast:
        """Return the channel's contrast, seeding from ``plane`` when missing.

        Seeding uses :func:`contrast_clip_min_max` for ``value_min``/``value_max``
        and the raw plane min/max for ``img_min``/``img_max``. The default
        seeding path does NOT mark the file dirty (only :meth:`set_image_contrast`
        does), so loading a file and viewing every channel never produces an
        unsolicited save prompt.

        Args:
            channel: Zero-based channel index.
            plane: 2D ndarray ``(Y, X)`` supplied by the caller. AcqImage never
                decodes its own slice for contrast.
            default_color_lut: LUT identifier used when no entry exists yet.
            percentile_low: Lower percentile for auto clipping.
            percentile_high: Upper percentile for auto clipping.

        Returns:
            Stored :class:`ImageContrast` for ``channel`` (existing or newly
            seeded).

        Raises:
            ValueError: If ``plane`` is empty.
        """
        key = int(channel)
        existing = self._image_contrasts.get(key)
        if existing is not None:
            return existing
        value_min, value_max = contrast_clip_min_max(
            plane,
            percentile_low=percentile_low,
            percentile_high=percentile_high,
        )
        contrast = ImageContrast(
            color_lut=str(default_color_lut),
            value_min=value_min,
            value_max=value_max,
            img_min=int(plane.min()),
            img_max=int(plane.max()),
        )
        self._image_contrasts[key] = contrast
        return contrast

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
        """Return the analysis set for this acquisition.

        The analysis set creates, stores, runs, removes, serializes, and saves
        analysis instances for this file. Analyses are keyed by analysis name,
        channel, and ROI identifier.
        """
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
            'saved': not self.is_dirty,
            'path': self.path,
            'parent': parent,
            'grandparent': grandparent,
            'condition': self._experimental_metadata.condition,
            'genotype': self._experimental_metadata.genotype,
            'num_channels': self._images.num_channels,
            'num_rois': self.rois.num_rois,
            'accept': self._accept,
        }
        validate_values_for_schema(self.get_schema(), values)
        return values

    def get_tree_rows(self) -> list[dict[str, object]]:
        """Return tree rows for this file and its analyses.

        Returns:
            Flat row list with the file row first, followed by one row per
            analysis in analysis insertion order.
        """
        rows: list[dict[str, object]] = [self._build_file_tree_row()]
        rows.extend(self._build_analysis_tree_rows())
        return rows

    def _build_file_tree_row(self) -> dict[str, object]:
        """Return the top-level tree row for this file.

        Returns:
            Row dictionary with tree contract fields plus schema-keyed file
            values.
        """
        return {
            ACQ_TREE_ROW_ID_FIELD: self.file_id,
            ACQ_TREE_PATH_FIELD: [self.file_id],
            ACQ_TREE_ROW_TYPE_FIELD: ACQ_TREE_ROW_TYPE_FILE,
            ACQ_TREE_ANALYSIS_NAME_FIELD: None,
            ACQ_TREE_ANALYSIS_CHANNEL_FIELD: None,
            ACQ_TREE_ANALYSIS_ROI_ID_FIELD: None,
            **self.get_schema_row(),
        }

    def _build_analysis_tree_rows(self) -> list[dict[str, object]]:
        """Return child tree rows for analyses owned by this file.

        Analysis-row display values:

        - ``name`` is set to the analysis identifier (e.g.
          ``"radon_velocity"``) so the tree disclosure column shows which
          analysis the child row represents.
        - ``num_channels`` and ``num_rois`` are overloaded for display in
          analysis rows: they carry the specific ``channel`` and
          ``roi_id`` used to compute the analysis, not counts. This makes
          the existing "Channels" / "ROIs" columns show the analysis
          identity components without adding new tree-only columns.

        Tree-row identity fields (``channel``, ``roi_id``,
        ``analysis_name``) remain the authoritative source of analysis
        identity for the controller and event system; the schema-field
        overloads are display-only.

        Returns:
            Row dictionaries with tree contract fields plus all file-list
            schema keys. Non-display schema keys are set to ``None``.
        """
        schema_keys = self.get_schema().field_names()
        rows: list[dict[str, object]] = []
        for analysis in self._acq_analysis_set.as_list():
            channel = int(analysis.key.channel)
            roi_id = int(analysis.key.roi_id)
            analysis_name = analysis.key.analysis_name
            row_id = build_analysis_tree_row_id(
                self.file_id,
                analysis_name,
                channel,
                roi_id,
            )
            row: dict[str, object] = {
                ACQ_TREE_ROW_ID_FIELD: row_id,
                ACQ_TREE_PATH_FIELD: [self.file_id, row_id],
                ACQ_TREE_ROW_TYPE_FIELD: ACQ_TREE_ROW_TYPE_ANALYSIS,
                ACQ_TREE_ANALYSIS_NAME_FIELD: analysis_name,
                ACQ_TREE_ANALYSIS_CHANNEL_FIELD: channel,
                ACQ_TREE_ANALYSIS_ROI_ID_FIELD: roi_id,
                'name': analysis_name,
                'num_channels': channel,
                'num_rois': roi_id,
            }
            for key in schema_keys:
                row.setdefault(key, None)
            rows.append(row)
        return rows

    def get_default_channel(self) -> int | None:
        """Return the default channel index for this file.

        Used by gui, generally not used in scripts.

        Returns:
            Zero-based channel index for the first channel, or ``None`` when the
            file exposes no channels.
        """
        return self._pixels.default_channel

    def get_default_roi(self) -> int | None:
        """Return the default ROI identifier for this file.

        Used by gui, generally not used in scripts.

        Returns:
            First ROI identifier in creation order, or ``None`` when no ROI
            exists.
        """
        roi_ids = self._rois.get_roi_ids()
        return roi_ids[0] if roi_ids else None

    def get_roi_image(self, channel: int, roi_id: int) -> np.ndarray:
        """Return full-resolution image data cropped to one rectangular ROI.

        This is the preferred scripting and analysis entry point for ROI-local
        image data. It uses source-resolution pixels, not the display pyramid
        used by the GUI for fast visualization. The current implementation reads
        slice ``z=0`` and ``t=0`` from the selected channel and clamps ROI bounds
        to the image bounds before cropping.

        Args:
            channel: Zero-based channel index.
            roi_id: Identifier of a :class:`~acqstore.acq_image.roi.RectROI`.

        Returns:
            Two-dimensional ``(Y, X)`` array cropped to the ROI. For kymographs,
            this is ``(time, space)`` in row/column order.

        Raises:
            ValueError: If ``roi_id`` is not present.
            TypeError: If the ROI is not a rectangular ROI.
        """
        # if not self.rois.has_roi(roi_id):
        #     raise ValueError(f'ROI {roi_id} not found')

        roi = self._rois.get(roi_id)
        if roi is None:
            raise ValueError(f'ROI {roi_id} not found')
        if isinstance(roi, LineROI):
            raise TypeError(
                f'get_roi_image requires a rectangular ROI; got LineROI (roi_id={roi_id})'
            )
        if not isinstance(roi, RectROI):
            raise TypeError(
                f'get_roi_image requires a rectangular ROI; got {type(roi).__name__} (roi_id={roi_id})'
            )
        bounds = roi.bounds.clamped_to(self._rois.image_bounds)
        return self._images.get_roi_rect_image(channel, bounds, z=0, t=0)

    def get_image_physical_units(self) -> tuple[float, float]:
        """Return physical pixel spacing for two-dimensional image data.

        The returned tuple is aligned with the array layout returned by
        :meth:`get_roi_image` and the file-loader slice APIs.

        Returns:
            ``(step_y, step_x)`` for ``(Y, X)`` arrays. For line-scan
            kymographs this is typically ``(seconds_per_line, microns_per_pixel)``.

        Raises:
            ValueError: If the file header does not define a ``Y``/``X`` plane.
        """
        return self._pixels.get_image_physical_units()

    def _infer_image_bounds(self) -> ImageBounds:
        """Infer image bounds from loaded header information.

        Returns:
            Image bounds built from known header dimensions.
        """
        sizes = self._pixels.header.sizes
        width = int(sizes.get('X', 1))
        height = int(sizes.get('Y', 1))
        num_slices = int(sizes.get('Z', 1))
        return ImageBounds(width=width, height=height, num_slices=num_slices)

    def _apply_image_header(self, header: ImageHeader) -> None:
        """Apply updated header to backing loader."""
        self._images.replace_header(header)