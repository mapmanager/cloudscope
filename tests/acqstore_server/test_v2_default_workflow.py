"""The visible runnable workflow should point users at API v2."""

from __future__ import annotations

from pathlib import Path

import acqstore_server.app as app_module
import acqstore_server.status_ui as status_ui_module


def test_cli_startup_text_points_to_v2_demo(monkeypatch, capsys) -> None:
    """Terminal startup advertises the maintained v2 demo and API docs."""
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(app_module, '_resolve_bind', lambda: ('127.0.0.1', 8767))
    monkeypatch.setattr(app_module, 'ensure_logging', lambda: None)
    monkeypatch.setattr(app_module, 'log_file_path', lambda: Path('/tmp/server.log'))
    monkeypatch.setattr(
        'uvicorn.run',
        lambda app, **kwargs: calls.append({'app': app, **kwargs}),
    )

    app_module.main_uvicorn()

    output = capsys.readouterr().out
    assert 'http://127.0.0.1:8767/demo/v2/' in output
    assert 'http://127.0.0.1:8767/docs' in output
    assert calls and calls[0]['port'] == 8767


def test_native_status_ui_source_targets_v2() -> None:
    """The packaged/native status UI opens v2 resources by default."""
    source = Path(status_ui_module.__file__).read_text(encoding='utf-8')
    assert "f'{base}/demo/v2/'" in source
    assert "f'{base}/api/v2/health'" in source
