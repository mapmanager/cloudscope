"""Acquisition object for non-image trace recording files."""

from __future__ import annotations

from pathlib import Path

from acqstore.acq_image.metadata import ExperimentMetadata
from acqstore.acq_trace.file_loaders.abf_trace_loader import AbfTraceLoader
from acqstore.acq_trace.sweep_data import SweepData
from acqstore.acq_trace.trace_header import TraceHeader


class AcqTrace:
    """Root object for one non-image trace acquisition file.

    ``AcqTrace`` is the trace/electrophysiology sibling of ``AcqImage``. It owns
    source-file metadata, experimental metadata, and lazy access to sweep data.
    It intentionally does not expose image pixels, image ROIs, image contrast,
    reference images, or image-specific analysis state.

    Args:
        path: Path to a supported trace recording file. Phase 1 supports ABF.
        accepted: Whether the file is accepted for downstream processing.
        experiment_metadata: Optional experimental metadata. Defaults to an
            empty :class:`ExperimentMetadata` instance.

    Raises:
        ValueError: If the file extension is unsupported.
        FileNotFoundError: If the path does not exist.
    """

    modality = 'trace'

    def __init__(
        self,
        path: str | Path,
        *,
        accepted: bool = True,
        experiment_metadata: ExperimentMetadata | None = None,
    ) -> None:
        self.path = str(Path(path).expanduser())
        self.accepted = bool(accepted)
        self.experiment_metadata = experiment_metadata or ExperimentMetadata()
        suffix = Path(self.path).suffix.lower()
        if suffix != '.abf':
            raise ValueError(f'Unsupported trace file extension: {suffix or "<none>"}')
        self._loader = AbfTraceLoader(self.path)

    @property
    def name(self) -> str:
        """Return the source file name.

        Returns:
            Basename of :attr:`path`.
        """
        return Path(self.path).name

    @property
    def file_id(self) -> str:
        """Return the stable file identifier for this trace.

        Returns:
            Current source path. This mirrors the simple file identity currently
            used by scripting code before mixed acquisition-list support lands.
        """
        return self.path

    @property
    def trace_header(self) -> TraceHeader:
        """Return trace header metadata.

        Returns:
            Immutable :class:`TraceHeader` for the source recording.
        """
        return self._loader.header

    def get_trace_header(self) -> TraceHeader:
        """Return trace header metadata.

        Returns:
            Immutable :class:`TraceHeader` for the source recording.
        """
        return self.trace_header

    def get_sweep(self, *, channel_index: int, sweep_index: int) -> SweepData:
        """Return one channel/sweep recording.

        Args:
            channel_index: Zero-based input channel index.
            sweep_index: Zero-based sweep index.

        Returns:
            :class:`SweepData` for the requested channel/sweep.

        Raises:
            ValueError: If either index is out of range.
        """
        return self._loader.get_sweep(channel_index=channel_index, sweep_index=sweep_index)

    def info(self) -> str:
        """Return a human-readable trace file summary.

        Returns:
            Multiline string describing the trace recording.
        """
        return self._loader.info()
