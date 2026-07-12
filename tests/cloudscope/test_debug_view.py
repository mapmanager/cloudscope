"""Tests for DebugView state read-out and disconnect/reconnect controls."""

from __future__ import annotations

import json
from types import SimpleNamespace

from cloudscope.controllers.home_page_controller import HomePageState
from cloudscope.session_state import HomePageChromeState, HomePageSessionSnapshot
from cloudscope.state import PrimarySelection
from cloudscope.views import debug_view as debug_view_module
from cloudscope.views.debug_view import (
    DebugView,
    _DISCONNECT_AND_RECONNECT_JS,
    _DISCONNECT_SECONDS,
    _MANUAL_DISCONNECT_JS,
    _MANUAL_RECONNECT_JS,
)
from cloudscope.views.view_ids import ViewId


def _stub_runtime(state: HomePageState, snapshot: HomePageSessionSnapshot | None):
    """Return a runtime-like object exposing the fields DebugView reads."""
    return SimpleNamespace(
        home_page_controller=SimpleNamespace(state=state),
        session_snapshot=snapshot,
    )


def test_debug_view_view_id() -> None:
    """DebugView should use the DEBUG view id."""
    assert DebugView.view_id is ViewId.DEBUG


def test_home_page_state_to_debug_dict() -> None:
    """HomePageState owns the diagnostic summary shaping, not the view."""
    state = HomePageState(
        file_ids=['a', 'b'],
        selection=PrimarySelection(file_id='a', channel=1, roi_id=2),
        acq_image_list=None,
        primary_x_range=(1.0, 4.0),
    )

    assert state.to_debug_dict() == {
        'selection': {
            'file_id': 'a',
            'channel': 1,
            'roi_id': 2,
            'analysis_name': None,
        },
        'primary_x_range': [1.0, 4.0],
        'file_count': 2,
        'acq_image_list_loaded': False,
    }


def test_collect_state_without_snapshot(monkeypatch) -> None:
    """State read-out reports live selection and a null snapshot when none captured."""
    state = HomePageState(
        file_ids=['a', 'b', 'c'],
        selection=PrimarySelection(file_id='a', channel=1, roi_id=2, analysis_name='radon_velocity'),
        acq_image_list=None,
        primary_x_range=(0.0, 5.0),
    )
    monkeypatch.setattr(
        debug_view_module, 'get_current_runtime', lambda: _stub_runtime(state, None)
    )

    collected = DebugView._collect_state()  # noqa: SLF001

    assert collected['live_home_page_state']['selection'] == {
        'file_id': 'a',
        'channel': 1,
        'roi_id': 2,
        'analysis_name': 'radon_velocity',
    }
    assert collected['live_home_page_state']['primary_x_range'] == [0.0, 5.0]
    assert collected['live_home_page_state']['file_count'] == 3
    assert collected['live_home_page_state']['acq_image_list_loaded'] is False
    assert collected['session_snapshot'] is None


def test_collect_state_with_snapshot(monkeypatch) -> None:
    """State read-out includes captured chrome and per-view blob keys."""
    state = HomePageState(file_ids=[], selection=PrimarySelection())
    snapshot = HomePageSessionSnapshot(
        chrome=HomePageChromeState.defaults(),
        views={'primary_image': {'zoom': 2}, 'sum_intensity_plot': {}},
    )
    monkeypatch.setattr(
        debug_view_module, 'get_current_runtime', lambda: _stub_runtime(state, snapshot)
    )

    collected = DebugView._collect_state()  # noqa: SLF001

    assert collected['session_snapshot']['view_ids'] == [
        'primary_image',
        'sum_intensity_plot',
    ]
    assert collected['session_snapshot']['views']['primary_image'] == {'zoom': 2}


def test_current_state_json_is_valid_json(monkeypatch) -> None:
    """The rendered read-out must be valid, indented JSON text."""
    state = HomePageState(file_ids=['x'], selection=PrimarySelection(file_id='x'))
    monkeypatch.setattr(
        debug_view_module, 'get_current_runtime', lambda: _stub_runtime(state, None)
    )

    view = DebugView(event_bus=None)
    text = view._current_state_json()  # noqa: SLF001

    parsed = json.loads(text)
    assert parsed['live_home_page_state']['selection']['file_id'] == 'x'


def test_current_state_json_handles_runtime_error(monkeypatch) -> None:
    """A missing runtime must degrade to a note, not raise."""
    def _boom():
        raise RuntimeError('no runtime')

    monkeypatch.setattr(debug_view_module, 'get_current_runtime', _boom)

    view = DebugView(event_bus=None)
    text = view._current_state_json()  # noqa: SLF001

    assert 'unavailable' in text


def test_disconnect_reconnect_js_uses_window_socket() -> None:
    """Primary test button must use public window.socket API, not engine internals."""
    assert 'window.socket.disconnect()' in _DISCONNECT_AND_RECONNECT_JS
    assert 'window.socket.connect()' in _DISCONNECT_AND_RECONNECT_JS
    assert 'socket.io.engine' not in _DISCONNECT_AND_RECONNECT_JS
    assert str(_DISCONNECT_SECONDS * 1000) in _DISCONNECT_AND_RECONNECT_JS


def test_manual_disconnect_js_uses_window_socket() -> None:
    """Manual disconnect must use window.socket.disconnect()."""
    assert 'window.socket.disconnect()' in _MANUAL_DISCONNECT_JS
    assert 'socket.io.engine' not in _MANUAL_DISCONNECT_JS


def test_manual_reconnect_js_uses_window_socket() -> None:
    """Manual reconnect must use window.socket.connect()."""
    assert 'window.socket.connect()' in _MANUAL_RECONNECT_JS
