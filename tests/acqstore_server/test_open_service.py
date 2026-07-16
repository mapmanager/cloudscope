"""Tests for AcqStore Server open_service."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from acqstore_server.open_service import OpenServiceError, open_path, parse_open_request
from acqstore_server.session_store import SessionStore


def _write_cyx_tif(path: Path, shape: tuple[int, int, int] = (2, 12, 8)) -> np.ndarray:
    """Write a CYX uint16 TIFF and return the array."""
    arr = np.arange(int(np.prod(shape)), dtype=np.uint16).reshape(shape)
    tifffile.imwrite(path, arr, metadata={'axes': 'CYX'}, photometric='minisblack')
    return arr


def _write_yx_tif(path: Path, shape: tuple[int, int] = (10, 6)) -> np.ndarray:
    arr = np.arange(int(np.prod(shape)), dtype=np.uint16).reshape(shape)
    tifffile.imwrite(path, arr, metadata={'axes': 'YX'}, photometric='minisblack')
    return arr


def test_open_path_dual_channel(tmp_path: Path) -> None:
    path = tmp_path / 'dual.tif'
    arr = _write_cyx_tif(path, shape=(2, 12, 8))
    store = SessionStore()

    payload = open_path(str(path), store)

    assert payload['ok'] is True
    assert payload['source']['numChannels'] == 2
    assert payload['source']['height'] == 12
    assert payload['source']['width'] == 8
    assert 'calcium' in payload['channels']
    assert 'vessels' in payload['channels']
    assert payload['channels']['calcium']['index'] == 0
    assert payload['channels']['vessels']['index'] == 1
    assert payload['reference'] is None
    assert payload['calibration']['unitsSource'] == 'acqimage'
    assert payload['calibration']['msPerLine'] == pytest.approx(
        payload['calibration']['stepYSeconds'] * 1000.0
    )
    cal = payload['calibration']
    assert cal['dim_0_step'] == pytest.approx(cal['stepYSeconds'])
    assert cal['dim_1_step'] == pytest.approx(cal['stepXUm'])
    assert isinstance(cal['dim_0_units'], str) and cal['dim_0_units'].strip()
    assert isinstance(cal['dim_1_units'], str) and cal['dim_1_units'].strip()

    sid = payload['sessionId']
    calcium = store.get_channel(sid, 'calcium')
    vessels = store.get_channel(sid, 'vessels')
    assert calcium is not None and vessels is not None
    assert len(calcium) == 12 * 8 * 4
    assert len(vessels) == 12 * 8 * 4

    c = np.frombuffer(calcium, dtype='<f4').reshape(12, 8)
    v = np.frombuffer(vessels, dtype='<f4').reshape(12, 8)
    np.testing.assert_allclose(c, arr[0].astype(np.float32))
    np.testing.assert_allclose(v, arr[1].astype(np.float32))


def test_open_path_single_channel_omits_vessels(tmp_path: Path) -> None:
    path = tmp_path / 'single.tif'
    _write_yx_tif(path)
    store = SessionStore()

    payload = open_path(str(path), store)

    assert payload['source']['numChannels'] == 1
    assert 'calcium' in payload['channels']
    assert 'vessels' not in payload['channels']
    assert store.get_channel(payload['sessionId'], 'vessels') is None


def test_open_path_vessel_channel_null_forces_single(tmp_path: Path) -> None:
    path = tmp_path / 'dual2.tif'
    _write_cyx_tif(path)
    store = SessionStore()

    payload = open_path(str(path), store, vessel_channel=None)

    assert payload['source']['numChannels'] == 2
    assert 'vessels' not in payload['channels']


def test_open_path_logs_header_summary(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / 'dual_log.tif'
    _write_cyx_tif(path, shape=(2, 12, 8))
    store = SessionStore()
    with caplog.at_level('INFO', logger='acqstore_server.open_service'):
        open_path(str(path), store)
    joined = '\n'.join(caplog.messages)
    assert 'Opened dual_log.tif' in joined
    assert '  dims=' in joined
    assert '  shape=' in joined
    assert '  msPerLine=' in joined
    assert '  umPerPixel=' in joined or 'msPerLine=' in joined
    assert '12x8' in joined
    assert '  reference=none' in joined



def test_open_path_channel_out_of_range(tmp_path: Path) -> None:
    path = tmp_path / 'dual3.tif'
    _write_cyx_tif(path)
    store = SessionStore()
    with pytest.raises(OpenServiceError) as exc_info:
        open_path(str(path), store, calcium_channel=5)
    assert exc_info.value.code == 'channel_out_of_range'


def test_parse_open_request_defaults() -> None:
    path, c, v = parse_open_request({'path': '/tmp/x.tif'})
    assert path == '/tmp/x.tif'
    assert c == 0
    assert v == 1


def test_parse_open_request_null_vessel() -> None:
    path, c, v = parse_open_request({'path': '/tmp/x.tif', 'vesselChannel': None})
    assert path == '/tmp/x.tif'
    assert c == 0
    assert v is None


def test_open_path_with_reference_monkeypatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When loader exposes a ReferenceImage, open payload includes reference + plane bytes."""
    from acqstore.acq_image.file_loaders.base_file_loader import BaseFileLoader, ReferenceImage

    path = tmp_path / 'with_ref.tif'
    _write_yx_tif(path, shape=(6, 5))
    store = SessionStore()

    ref_array = np.arange(8 * 9, dtype=np.float32).reshape(8, 9)
    reference = ReferenceImage(
        array=ref_array,
        dims=('Y', 'X'),
        num_channels=1,
        line_roi=(1.0, 2.0, 7.0, 6.0),
        coord_units=(('X', 'um'), ('Y', 'um')),
        coord_scales=(('X', 0.25), ('Y', 0.5)),
        coords=(),
        scan_path=np.asarray([[1.0, 7.0], [2.0, 6.0]], dtype=float),
    )

    monkeypatch.setattr(
        BaseFileLoader,
        'has_reference_image',
        property(lambda self: True),
    )
    monkeypatch.setattr(
        BaseFileLoader,
        'reference_image',
        property(lambda self: reference),
    )

    with caplog.at_level('INFO', logger='acqstore_server.open_service'):
        payload = open_path(str(path), store)
    assert payload['reference'] is not None
    assert payload['reference']['numChannels'] == 1
    assert payload['reference']['height'] == 8
    assert payload['reference']['width'] == 9
    assert payload['reference']['lineRoi'] == [1.0, 2.0, 7.0, 6.0]
    assert payload['reference']['scanPath'] is not None
    assert payload['reference']['scanPath']['x'] == [1.0, 7.0]
    assert payload['reference']['scanPath']['y'] == [2.0, 6.0]
    assert '  reference lineRoi=[1.0, 2.0, 7.0, 6.0]' in caplog.messages
    assert len(payload['reference']['channels']) == 1
    assert payload['reference']['channels'][0]['index'] == 0

    plane = store.get_reference(payload['sessionId'])
    assert plane is not None
    np.testing.assert_allclose(
        np.frombuffer(plane, dtype='<f4').reshape(8, 9),
        ref_array,
    )


def test_open_path_multi_channel_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from acqstore.acq_image.file_loaders.base_file_loader import BaseFileLoader, ReferenceImage

    path = tmp_path / 'with_ref_multi.tif'
    _write_yx_tif(path, shape=(6, 5))
    store = SessionStore()

    ch0 = np.arange(4 * 5, dtype=np.float32).reshape(4, 5)
    ch1 = ch0 + 100.0
    reference = ReferenceImage(
        array=np.stack([ch0, ch1], axis=0),
        dims=('C', 'Y', 'X'),
        num_channels=2,
        line_roi=(0.0, 0.0, 4.0, 3.0),
        coord_units=(('X', 'um'), ('Y', 'um')),
        coord_scales=(('X', 0.25), ('Y', 0.5)),
        coords=(),
        scan_path=np.asarray([[0.0, 4.0], [0.0, 3.0]], dtype=float),
    )
    monkeypatch.setattr(
        BaseFileLoader, 'has_reference_image', property(lambda self: True)
    )
    monkeypatch.setattr(
        BaseFileLoader, 'reference_image', property(lambda self: reference)
    )

    payload = open_path(str(path), store)
    ref = payload['reference']
    assert ref is not None
    assert ref['numChannels'] == 2
    assert len(ref['channels']) == 2
    assert ref['channels'][0]['url'].endswith('/reference/channel/0')
    assert ref['channels'][1]['url'].endswith('/reference/channel/1')
    assert 'url' not in ref

    sid = payload['sessionId']
    b0 = store.get_reference(sid, 0)
    b1 = store.get_reference(sid, 1)
    assert b0 is not None and b1 is not None
    np.testing.assert_allclose(np.frombuffer(b0, dtype='<f4').reshape(4, 5), ch0)
    np.testing.assert_allclose(np.frombuffer(b1, dtype='<f4').reshape(4, 5), ch1)
