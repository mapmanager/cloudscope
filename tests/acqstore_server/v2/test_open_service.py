"""Tests for the transport-neutral AcqStore Server API v2 open service."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from acqstore_server.v2.open_service import OpenServiceError, open_acquisition


def _write_cyx_tif(path: Path, shape: tuple[int, int, int] = (3, 12, 8)) -> np.ndarray:
    array = np.arange(int(np.prod(shape)), dtype=np.uint16).reshape(shape)
    tifffile.imwrite(path, array, metadata={'axes': 'CYX'}, photometric='minisblack')
    return array


def _write_yx_tif(path: Path, shape: tuple[int, int] = (10, 6)) -> np.ndarray:
    array = np.arange(int(np.prod(shape)), dtype=np.uint16).reshape(shape)
    tifffile.imwrite(path, array, metadata={'axes': 'YX'}, photometric='minisblack')
    return array


def test_open_all_channels_by_default(tmp_path: Path) -> None:
    path = tmp_path / 'all.tif'
    source = _write_cyx_tif(path)

    opened = open_acquisition(str(path))

    assert opened.num_source_channels == 3
    assert [channel.index for channel in opened.channels] == [0, 1, 2]
    assert [channel.name for channel in opened.channels] == ['CH1', 'CH2', 'CH3']
    assert opened.source_dtype == 'uint16'
    for index, channel in enumerate(opened.channels):
        assert channel.array.dtype == np.uint16
        np.testing.assert_array_equal(channel.array, source[index])


def test_requested_channel_order_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / 'ordered.tif'
    source = _write_cyx_tif(path)

    opened = open_acquisition(str(path), channel_indices=[2, 0])

    assert [channel.index for channel in opened.channels] == [2, 0]
    np.testing.assert_array_equal(opened.channels[0].array, source[2])
    np.testing.assert_array_equal(opened.channels[1].array, source[0])


def test_single_channel_tiff(tmp_path: Path) -> None:
    path = tmp_path / 'single.tif'
    source = _write_yx_tif(path)

    opened = open_acquisition(str(path))

    assert opened.num_source_channels == 1
    assert len(opened.channels) == 1
    np.testing.assert_array_equal(opened.channels[0].array, source)
    assert [axis.array_dimension for axis in opened.axes] == [0, 1]
    assert [axis.name for axis in opened.axes] == ['Y', 'X']
    assert [axis.size for axis in opened.axes] == list(source.shape)
    assert all(axis.step > 0 for axis in opened.axes)
    assert all(axis.unit.strip() for axis in opened.axes)


@pytest.mark.parametrize(
    ('indices', 'code'),
    [
        ([], 'invalid_channel_indices'),
        ([0, 0], 'invalid_channel_indices'),
        ([-1], 'invalid_channel_indices'),
        ([9], 'channel_out_of_range'),
    ],
)
def test_invalid_channel_selections(
    tmp_path: Path,
    indices: list[int],
    code: str,
) -> None:
    path = tmp_path / 'invalid.tif'
    _write_cyx_tif(path)

    with pytest.raises(OpenServiceError) as exc_info:
        open_acquisition(str(path), channel_indices=indices)

    assert exc_info.value.code == code


def test_internal_models_have_no_http_urls_or_client_roles(tmp_path: Path) -> None:
    path = tmp_path / 'neutral.tif'
    _write_cyx_tif(path)

    opened = open_acquisition(str(path), channel_indices=[0, 1])
    text = repr(opened).lower()

    assert 'http' not in text
    assert 'url=' not in text
    assert 'calcium' not in text
    assert 'vessel' not in text


def test_directory_backed_acquisition_path_is_not_rejected_as_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from acqstore_server.v2 import open_service

    path = tmp_path / 'example.ome.zarr'
    path.mkdir()

    class LoaderReachedError(ValueError):
        pass

    def fake_acq_image(*_args: object, **_kwargs: object) -> object:
        raise LoaderReachedError('loader was reached')

    monkeypatch.setattr(open_service, 'AcqImage', fake_acq_image)

    with pytest.raises(OpenServiceError) as exc_info:
        open_acquisition(str(path))

    assert exc_info.value.code == 'unsupported_format'
    assert 'loader was reached' in exc_info.value.message


def test_compound_ome_zarr_format_uses_acqstore_normalization(tmp_path: Path) -> None:
    from acqstore_server.v2.open_service import _format_from_path

    assert _format_from_path(tmp_path / 'sample.ome.zarr') == 'ome.zarr'
    assert _format_from_path(tmp_path / 'sample.cs.ome.zarr') == 'cs.ome.zarr'
    assert _format_from_path(tmp_path / 'sample.ome.zarr.zip') == 'ome.zarr.zip'
