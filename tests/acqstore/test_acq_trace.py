"""Tests for the AcqTrace public API."""

from __future__ import annotations

from pathlib import Path

import pytest

from acqstore.acq_image.metadata import ExperimentMetadata
from acqstore.acq_trace.acq_trace import AcqTrace
from acqstore.acq_trace.epoch_data import EpochInterval, EpochTable
from acqstore.acq_trace.sweep_data import SweepData
from acqstore.acq_trace.trace_header import TraceHeader

ABF_DATA_DIR = Path(__file__).parent / 'data' / 'abf'
ABF_0016 = ABF_DATA_DIR / '2021_07_20_0016.abf'


def test_acq_trace_constructs_from_abf_and_exposes_header() -> None:
    """AcqTrace should expose basic trace identity and header metadata."""
    trace = AcqTrace(ABF_0016)

    assert trace.modality == 'trace'
    assert trace.path == str(ABF_0016)
    assert trace.name == '2021_07_20_0016.abf'
    assert trace.file_id == str(ABF_0016)
    assert trace.accepted is True
    assert isinstance(trace.experiment_metadata, ExperimentMetadata)
    assert trace.get_trace_header().num_sweeps == 17
    assert trace.trace_header.num_channels == 2


def test_acq_trace_preserves_constructor_state() -> None:
    """AcqTrace should preserve accepted state and provided metadata object."""
    metadata = ExperimentMetadata(species='mouse', condition='test')

    trace = AcqTrace(ABF_0016, accepted=False, experiment_metadata=metadata)

    assert trace.accepted is False
    assert trace.experiment_metadata is metadata
    assert trace.experiment_metadata.species == 'mouse'
    assert trace.experiment_metadata.condition == 'test'


def test_acq_trace_get_sweep_delegates_to_loader() -> None:
    """AcqTrace should return SweepData from the underlying ABF loader."""
    trace = AcqTrace(ABF_0016)

    sweep = trace.get_sweep(channel_index=0, sweep_index=0)

    assert isinstance(sweep, SweepData)
    assert sweep.num_samples == 1_600
    assert sweep.value_units == 'mV'
    assert sweep.command_values is not None


def test_acq_trace_info_returns_loader_summary() -> None:
    """AcqTrace info should provide a script-friendly file overview."""
    trace = AcqTrace(ABF_0016)

    info = trace.info()

    assert 'ABF Trace File' in info
    assert 'sweeps: 17' in info
    assert 'Vm_scaled' in info
    assert 'I_Clamp' in info


def test_acq_trace_rejects_unsupported_extension(tmp_path: Path) -> None:
    """AcqTrace should fail fast for unsupported trace file types."""
    text_path = tmp_path / 'not_abf.txt'
    text_path.write_text('not an abf file')

    with pytest.raises(ValueError, match='Unsupported trace file extension'):
        AcqTrace(text_path)


def test_trace_header_validates_channel_metadata_lengths() -> None:
    """TraceHeader should reject inconsistent channel metadata."""
    with pytest.raises(ValueError, match='channel_names length'):
        TraceHeader(
            path='x.abf',
            file_size='1 KB',
            num_sweeps=1,
            num_channels=2,
            samples_per_second=10_000,
            samples_per_sweep=100,
            channel_names=('Vm',),
            channel_units=('mV', 'pA'),
            command_names=('Cmd',),
            command_units=('nA',),
        )


def test_epoch_table_generates_per_sample_labels() -> None:
    """EpochTable should convert intervals to one label per sample."""
    table = EpochTable(
        (
            EpochInterval(0, 0, 2, -0.2, 'Step'),
            EpochInterval(1, 2, 5, -0.7, 'Step'),
        )
    )

    labels = table.to_sample_labels(6)

    assert labels.tolist() == [0, 0, 1, 1, 1, -1]
    assert table.to_dicts()[1]['epoch_type'] == 'Step'


def test_epoch_interval_rejects_empty_interval() -> None:
    """EpochInterval should reject intervals without positive length."""
    with pytest.raises(ValueError, match='end_sample must be greater'):
        EpochInterval(0, 10, 10, 0.0, 'Step')


def test_epoch_table_rejects_interval_beyond_num_samples() -> None:
    """EpochTable labels should reject intervals beyond the target sweep."""
    table = EpochTable((EpochInterval(0, 0, 10, 0.0, 'Step'),))

    with pytest.raises(ValueError, match='extends beyond sweep samples'):
        table.to_sample_labels(9)
