"""Download and prepare reusable AcqStore sample datasets.

This module is intentionally GUI-independent. Applications such as CloudScope
can call :func:`ensure_sample` and then pass the returned folder path to
``AcqImageList`` using the same code path as a user-selected folder.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import zipfile

from platformdirs import user_data_dir


SAMPLE_DATA_DIR_ENV = 'CLOUDSCOPE_SAMPLE_DATA_DIR'
DEFAULT_APP_NAME = 'cloudscope'

DIAMETER_SAMPLE_DATA = 'diameter-sample-data'
VELOCITY_SAMPLE_DATA = 'velocity-sample-data'

_RELEASE_BASE = 'https://github.com/mapmanager/cloudscope-data/releases/download/v0.1.0'


@dataclass(frozen=True, slots=True)
class SampleDataset:
    """Registry entry for one downloadable sample dataset.

    Attributes:
        name: Stable user-facing sample key.
        version: Dataset archive/cache version. Bump when archive contents change.
        url: Remote zip archive URL.
        sha256: Expected archive SHA-256 digest, without the ``sha256:`` prefix.
        extracted_dir: Directory inside the extracted archive that AcqImageList can load.
        description: Short description suitable for UI labels/help text.
    """

    name: str
    version: str
    url: str
    sha256: str
    extracted_dir: str
    description: str = ''

    @property
    def cache_key(self) -> str:
        """Return versioned cache directory name for this sample."""
        return f'{self.name}-{self.version}'

    @property
    def archive_filename(self) -> str:
        """Return deterministic local archive filename."""
        return f'{self.name}-{self.version}.zip'

    @property
    def known_hash(self) -> str:
        """Return Pooch-compatible hash string."""
        return f'sha256:{self.sha256}'


SAMPLES: dict[str, SampleDataset] = {
    DIAMETER_SAMPLE_DATA: SampleDataset(
        name=DIAMETER_SAMPLE_DATA,
        version='v1',
        url=f'{_RELEASE_BASE}/diameter-sample-data.zip',
        sha256='0d897008319e998ddabc383abb1245f8fefe5b9655f44de1b094f09cfe464d7a',
        extracted_dir=DIAMETER_SAMPLE_DATA,
        description='TIF kymograph sample data for diameter analysis demos.',
    ),
    VELOCITY_SAMPLE_DATA: SampleDataset(
        name=VELOCITY_SAMPLE_DATA,
        version='v1',
        url=f'{_RELEASE_BASE}/velocity-sample-data.zip',
        sha256='a8223a2c7984bd43ef3df882e7f9f7216459341b76285af4286ff809a5d64941',
        extracted_dir=VELOCITY_SAMPLE_DATA,
        description='OIR kymograph sample data for velocity analysis demos.',
    ),
}


class SampleDataError(RuntimeError):
    """Base error for sample-data operations."""


class UnknownSampleError(SampleDataError):
    """Raised when a requested sample name is not registered."""


def list_samples() -> tuple[SampleDataset, ...]:
    """Return registered sample datasets in stable name order."""
    return tuple(SAMPLES[name] for name in sorted(SAMPLES))


def get_sample(name: str) -> SampleDataset:
    """Return one registered sample dataset.

    Args:
        name: Registered sample name.

    Returns:
        Sample dataset definition.

    Raises:
        UnknownSampleError: If ``name`` is not registered.
    """
    try:
        return SAMPLES[name]
    except KeyError as exc:
        known = ', '.join(sorted(SAMPLES)) or '<none>'
        raise UnknownSampleError(f'Unknown sample dataset {name!r}; known samples: {known}') from exc


def get_sample_data_dir() -> Path:
    """Return root directory used for downloaded sample data.

    Resolution order:

    1. ``CLOUDSCOPE_SAMPLE_DATA_DIR`` when set.
    2. ``platformdirs.user_data_dir("cloudscope") / "sample-data"``.

    On macOS the default is usually
    ``~/Library/Application Support/cloudscope/sample-data``.
    """
    env_path = os.getenv(SAMPLE_DATA_DIR_ENV)
    if env_path:
        return Path(env_path).expanduser().resolve(strict=False)
    return Path(user_data_dir(DEFAULT_APP_NAME)) / 'sample-data'


def ensure_sample(name: str, *, sample_data_dir: str | Path | None = None) -> Path:
    """Ensure a sample dataset is downloaded/extracted and return its load folder.

    Args:
        name: Registered sample name.
        sample_data_dir: Optional cache root override. Primarily useful for tests
            or scripts; deployment should normally use ``CLOUDSCOPE_SAMPLE_DATA_DIR``.

    Returns:
        Local folder path that can be passed to ``AcqImageList`` as a folder.

    Raises:
        UnknownSampleError: If ``name`` is not registered.
        SampleDataError: If the archive cannot be downloaded, validated, or
            extracted into the expected directory.
    """
    sample = get_sample(name)
    root = Path(sample_data_dir).expanduser().resolve(strict=False) if sample_data_dir is not None else get_sample_data_dir()
    sample_root = root / sample.cache_key
    load_path = sample_root / sample.extracted_dir
    marker_path = sample_root / '.cloudscope_sample_extracted'

    if load_path.is_dir() and marker_path.is_file():
        return load_path

    sample_root.mkdir(parents=True, exist_ok=True)
    archive_path = _retrieve_archive(sample, sample_root / '_archives')
    _extract_zip(archive_path, sample_root)

    if not load_path.is_dir():
        raise SampleDataError(
            f'Sample {sample.name!r} did not extract expected directory {sample.extracted_dir!r} from {archive_path}'
        )

    marker_path.write_text(f'{sample.name}\n{sample.version}\n{sample.sha256}\n', encoding='utf-8')
    return load_path


def _retrieve_archive(sample: SampleDataset, archive_dir: Path) -> Path:
    """Download/validate archive with Pooch and return local archive path."""
    try:
        import pooch
    except ImportError as exc:  # pragma: no cover - exercised only without optional dependency
        raise SampleDataError('Sample data support requires the pooch package. Install with: uv add pooch') from exc

    archive_dir.mkdir(parents=True, exist_ok=True)
    try:
        path = pooch.retrieve(
            url=sample.url,
            known_hash=sample.known_hash,
            fname=sample.archive_filename,
            path=archive_dir,
        )
    except Exception as exc:  # pragma: no cover - exact exception types vary by transport/hash failure
        raise SampleDataError(f'Could not retrieve sample dataset {sample.name!r}: {exc}') from exc
    return Path(path)


def _extract_zip(archive_path: Path, destination: Path) -> None:
    """Safely extract ``archive_path`` into ``destination``.

    Existing sample contents are replaced atomically enough for local app usage:
    extraction happens into a temporary sibling directory, then extracted entries
    are moved into ``destination``.
    """
    destination.mkdir(parents=True, exist_ok=True)
    tmp_dir = destination / '._extracting'
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.infolist():
                _validate_zip_member(member.filename)
            zf.extractall(tmp_dir)

        for child in tmp_dir.iterdir():
            target = destination / child.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            child.replace(target)
    except zipfile.BadZipFile as exc:
        raise SampleDataError(f'Sample archive is not a valid zip file: {archive_path}') from exc
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


def _validate_zip_member(name: str) -> None:
    """Reject zip entries that would escape the extraction directory."""
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise SampleDataError(f'Unsafe path in sample archive: {name!r}')
