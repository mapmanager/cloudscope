"""Tests for AcqStore sample-data download/extract helpers."""

from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

import acqstore.sample_data as sample_data_module
from acqstore.sample_data import (
    SampleDataError,
    SampleDataset,
    UnknownSampleError,
    ensure_sample,
    get_sample,
    get_sample_data_dir,
    list_samples,
)


def _make_zip(path: Path, *, root_name: str = 'demo-small') -> None:
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr(f'{root_name}/cond1/a.oir', 'raw')
        zf.writestr(f'{root_name}/cond1/a.oir.json', '{}')


def test_list_samples_includes_demo_small() -> None:
    samples = list_samples()
    names = [item.name for item in samples]
    assert 'demo-small' in names


def test_get_sample_returns_registered_sample() -> None:
    sample = get_sample('demo-small')
    assert sample.name == 'demo-small'
    assert sample.extracted_dir == 'demo-small'


def test_get_sample_raises_for_unknown_sample() -> None:
    with pytest.raises(UnknownSampleError, match='Unknown sample dataset'):
        get_sample('missing')


def test_get_sample_data_dir_uses_env_override(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv('CLOUDSCOPE_SAMPLE_DATA_DIR', str(tmp_path / 'sample-cache'))
    assert get_sample_data_dir() == (tmp_path / 'sample-cache').resolve(strict=False)


def test_ensure_sample_extracts_archive_and_returns_extracted_dir(tmp_path, monkeypatch) -> None:
    archive = tmp_path / 'archive.zip'
    _make_zip(archive)
    sample = SampleDataset(
        name='unit-sample',
        version='v1',
        url='https://example.invalid/unit-sample-v1.zip',
        sha256='abc',
        extracted_dir='demo-small',
    )

    monkeypatch.setitem(sample_data_module.SAMPLES, sample.name, sample)
    monkeypatch.setattr('acqstore.sample_data._retrieve_archive', lambda _sample, _archive_dir: archive)

    load_path = ensure_sample(sample.name, sample_data_dir=tmp_path / 'cache')

    assert load_path == tmp_path / 'cache' / 'unit-sample-v1' / 'demo-small'
    assert (load_path / 'cond1' / 'a.oir').is_file()
    assert (tmp_path / 'cache' / 'unit-sample-v1' / '.cloudscope_sample_extracted').is_file()


def test_ensure_sample_reuses_existing_extracted_sample(tmp_path, monkeypatch) -> None:
    sample = SampleDataset(
        name='unit-sample',
        version='v1',
        url='https://example.invalid/unit-sample-v1.zip',
        sha256='abc',
        extracted_dir='demo-small',
    )
    load_path = tmp_path / 'cache' / 'unit-sample-v1' / 'demo-small'
    load_path.mkdir(parents=True)
    marker = tmp_path / 'cache' / 'unit-sample-v1' / '.cloudscope_sample_extracted'
    marker.write_text('done', encoding='utf-8')

    def _fail_retrieve(_sample, _archive_dir):
        raise AssertionError('should not retrieve when marker and folder exist')

    monkeypatch.setitem(sample_data_module.SAMPLES, sample.name, sample)
    monkeypatch.setattr('acqstore.sample_data._retrieve_archive', _fail_retrieve)

    assert ensure_sample(sample.name, sample_data_dir=tmp_path / 'cache') == load_path


def test_ensure_sample_raises_when_expected_directory_missing(tmp_path, monkeypatch) -> None:
    archive = tmp_path / 'archive.zip'
    _make_zip(archive, root_name='unexpected-root')
    sample = SampleDataset(
        name='unit-sample',
        version='v1',
        url='https://example.invalid/unit-sample-v1.zip',
        sha256='abc',
        extracted_dir='demo-small',
    )
    monkeypatch.setitem(sample_data_module.SAMPLES, sample.name, sample)
    monkeypatch.setattr('acqstore.sample_data._retrieve_archive', lambda _sample, _archive_dir: archive)

    with pytest.raises(SampleDataError, match='did not extract expected directory'):
        ensure_sample(sample.name, sample_data_dir=tmp_path / 'cache')


def test_ensure_sample_rejects_unsafe_zip_member(tmp_path, monkeypatch) -> None:
    archive = tmp_path / 'archive.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('../evil.txt', 'bad')
    sample = SampleDataset(
        name='unit-sample',
        version='v1',
        url='https://example.invalid/unit-sample-v1.zip',
        sha256='abc',
        extracted_dir='demo-small',
    )
    monkeypatch.setitem(sample_data_module.SAMPLES, sample.name, sample)
    monkeypatch.setattr('acqstore.sample_data._retrieve_archive', lambda _sample, _archive_dir: archive)

    with pytest.raises(SampleDataError, match='Unsafe path'):
        ensure_sample(sample.name, sample_data_dir=tmp_path / 'cache')
