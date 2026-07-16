"""Native ``ui.run`` kwargs must not enable GZip on binary session GETs."""

from __future__ import annotations

from acqstore_server.app import native_ui_run_kwargs


def test_native_ui_run_kwargs_disables_gzip_middleware() -> None:
    """NiceGUI defaults install GZipMiddleware; we must opt out.

    With the default middleware, browsers negotiate gzip and Starlette
    compresses the full response before sending headers. Real ~20 MB float32
    planes can take ~15–20 s per GET at compresslevel=9.
    """
    kwargs = native_ui_run_kwargs(host='127.0.0.1', port=8767)
    assert kwargs['gzip_middleware_factory'] is None
    assert kwargs['native'] is True
    assert kwargs['reload'] is False
    assert kwargs['host'] == '127.0.0.1'
    assert kwargs['port'] == 8767
    assert kwargs['window_size'] == (560, 640)
