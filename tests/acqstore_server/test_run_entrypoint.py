"""Runnable server entry-point contract."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import acqstore_server.app as app_module


def test_main_uvicorn_prints_v2_demo_and_runs_server(monkeypatch, capsys) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(app: object, **kwargs: object) -> None:
        calls.append({'app': app, **kwargs})

    monkeypatch.setattr(app_module, '_resolve_bind', lambda: ('127.0.0.1', 8767))
    monkeypatch.setitem(sys.modules, 'uvicorn', SimpleNamespace(run=fake_run))

    app_module.main_uvicorn()

    output = capsys.readouterr().out
    assert 'http://127.0.0.1:8767/demo/v2/' in output
    assert 'http://127.0.0.1:8767/docs' in output
    assert calls == [
        {
            'app': app_module.app,
            'host': '127.0.0.1',
            'port': 8767,
            'log_level': 'info',
        }
    ]
