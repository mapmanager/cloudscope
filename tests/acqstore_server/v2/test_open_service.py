"""Deterministic unit tests for the v2 AcqStore adapter.

These tests replace microscope-file decoding with a small fake that mirrors the
public AcqImage surface consumed by ``open_acquisition``. Format decoding itself
belongs to AcqStore's own test suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from acqstore_server.v2.open_service import OpenServiceError, open_acquisition


@dataclass
class _Header:
    dims: tuple[str, ...] = ('C', 'Y', 'X')
    physical_units_labels: tuple[str, ...] = ('', 'um', 'um')

    def as_json_dict(self) -> dict[str, object]:
        return {
            'path': '/tmp/sample.tif',
            'shape': [2, 5, 4],
            'dims': ['C', 'Y', 'X'],
            'sizes': {'C': 2, 'Y': 5, 'X': 4},
            'dtype': 'uint16',
            'num_channels': 2,
            'physical_units': [1.0, 0.25, 0.5],
            'physical_units_labels': ['Channels', 'um', 'um'],
            'date': '20260717',
            'time': '11:30:00',
            'file_size': '1.2 MB',
        }


class _Pixels:
    def __init__(self, planes: tuple[np.ndarray, ...]) -> None:
        self._planes = planes
        self.num_channels = len(planes)

    def get_plane(self, *, c: int) -> np.ndarray:
        return self._planes[c]


class _Images:
    def __init__(self) -> None:
        self.header = _Header()
        self.has_reference_image = False
        self.reference_image = None


class _FakeAcqImage:
    def __init__(self, planes: tuple[np.ndarray, ...]) -> None:
        self.pixels = _Pixels(planes)
        self.images = _Images()

    def get_image_physical_units(self) -> tuple[float, float]:
        return (0.25, 0.5)


def _install_fake_acq_image(
    monkeypatch: pytest.MonkeyPatch,
    planes: tuple[np.ndarray, ...],
) -> None:
    from acqstore_server.v2 import open_service

    monkeypatch.setattr(
        open_service,
        'AcqImage',
        lambda *_args, **_kwargs: _FakeAcqImage(planes),
    )


def _existing_path(tmp_path: Path, name: str = 'sample.tif') -> Path:
    path = tmp_path / name
    path.write_bytes(b'fixture contents are not decoded by this unit test')
    return path


def test_open_all_channels_by_default_through_public_adapter_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planes = (
        np.arange(20, dtype=np.uint16).reshape(5, 4),
        np.arange(20, 40, dtype=np.uint16).reshape(5, 4),
    )
    _install_fake_acq_image(monkeypatch, planes)

    opened = open_acquisition(str(_existing_path(tmp_path)))

    assert opened.num_source_channels == 2
    assert [channel.index for channel in opened.channels] == [0, 1]
    assert [channel.name for channel in opened.channels] == ['CH1', 'CH2']
    assert opened.source_dtype == 'uint16'
    assert opened.header.dims == ('C', 'Y', 'X')
    assert opened.header.sizes == {'C': 2, 'Y': 5, 'X': 4}
    assert opened.header.physical_units == (1.0, 0.25, 0.5)
    assert [(axis.name, axis.size, axis.step, axis.unit) for axis in opened.axes] == [
        ('Y', 5, 0.25, 'um'),
        ('X', 4, 0.5, 'um'),
    ]
    np.testing.assert_array_equal(opened.channels[0].array, planes[0])
    np.testing.assert_array_equal(opened.channels[1].array, planes[1])


def test_requested_channel_order_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planes = tuple(
        np.full((3, 2), fill_value=index, dtype=np.uint16) for index in range(3)
    )
    _install_fake_acq_image(monkeypatch, planes)

    opened = open_acquisition(
        str(_existing_path(tmp_path)),
        channel_indices=[2, 0],
    )

    assert [channel.index for channel in opened.channels] == [2, 0]
    np.testing.assert_array_equal(opened.channels[0].array, planes[2])
    np.testing.assert_array_equal(opened.channels[1].array, planes[0])


@pytest.mark.parametrize(
    ('indices', 'code'),
    [
        ([], 'invalid_channel_indices'),
        ([0, 0], 'invalid_channel_indices'),
        ([-1], 'invalid_channel_indices'),
        ([9], 'channel_out_of_range'),
    ],
)
def test_invalid_channel_selections_are_server_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    indices: list[int],
    code: str,
) -> None:
    _install_fake_acq_image(
        monkeypatch,
        (np.zeros((3, 2), dtype=np.uint16),),
    )

    with pytest.raises(OpenServiceError) as exc_info:
        open_acquisition(str(_existing_path(tmp_path)), channel_indices=indices)

    assert exc_info.value.code == code


def test_internal_models_have_no_http_urls_or_client_roles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_acq_image(
        monkeypatch,
        (np.zeros((3, 2), dtype=np.uint16),),
    )

    opened = open_acquisition(str(_existing_path(tmp_path)))
    text = repr(opened).lower()

    assert 'http' not in text
    assert 'url=' not in text
    assert 'calcium' not in text
    assert 'vessel' not in text


def test_directory_backed_acquisition_path_reaches_acqstore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from acqstore_server.v2 import open_service

    path = tmp_path / 'example.ome.zarr'
    path.mkdir()

    def fake_acq_image(*_args: object, **_kwargs: object) -> object:
        raise ValueError('loader was reached')

    monkeypatch.setattr(open_service, 'AcqImage', fake_acq_image)

    with pytest.raises(OpenServiceError) as exc_info:
        open_acquisition(str(path))

    assert exc_info.value.code == 'unsupported_format'
    assert 'loader was reached' in exc_info.value.message


def test_compound_format_uses_acqstore_normalization(tmp_path: Path) -> None:
    from acqstore_server.v2.open_service import _format_from_path

    assert _format_from_path(tmp_path / 'sample.ome.zarr') == 'ome.zarr'
    assert _format_from_path(tmp_path / 'sample.cs.ome.zarr') == 'cs.ome.zarr'
    assert _format_from_path(tmp_path / 'sample.ome.zarr.zip') == 'ome.zarr.zip'
