"""Minimal NiceGUI status window for AcqStore Server (server's own UI)."""

from __future__ import annotations

import os
import platform
import subprocess
import webbrowser
from pathlib import Path

from nicegui import app as nicegui_app
from nicegui import ui

from acqstore_server.logging_setup import get_logger, log_file_path
from acqstore_server.routes import APP_NAME, APP_VERSION

logger = get_logger('status_ui')


def _open_path_with_default_app(path: Path) -> None:
    """Open ``path`` with the OS default application (same idea as CloudScope).

    Args:
        path: Existing file or directory path.
    """
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(str(resolved))
    system = platform.system()
    if system == 'Darwin':
        subprocess.run(['open', str(resolved)], check=False)
    elif system == 'Windows':
        os.startfile(resolved)  # type: ignore[attr-defined]
    else:
        subprocess.run(['xdg-open', str(resolved)], check=False)


def build_status_page(*, host: str, port: int) -> None:
    """Build the native/status page widgets.

    Args:
        host: Bind host shown to the user.
        port: Bind port.
    """
    base = f'http://{host}:{port}'
    log_path = log_file_path()

    ui.colors(primary='#38bdf8')
    with ui.column().classes('w-full max-w-xl p-4 gap-3'):
        ui.label('AcqStore Server').classes('text-h5 text-primary')
        ui.label(f'{APP_NAME} v{APP_VERSION}').classes('text-caption text-grey-5')
        ui.separator()
        ui.label(f'Status: listening on {base}').classes('text-body1')
        ui.label(f'Log file: {log_path}').classes('text-caption text-grey-5 break-all')

        with ui.row().classes('gap-2 flex-wrap'):
            ui.button(
                'Open demo',
                on_click=lambda: webbrowser.open(f'{base}/demo/'),
            ).props('color=primary')
            ui.button(
                'API docs (/docs)',
                on_click=lambda: webbrowser.open(f'{base}/docs'),
            ).props('outline')
            ui.button(
                'Open health JSON',
                on_click=lambda: webbrowser.open(f'{base}/api/v1/health'),
            ).props('outline')

            def _open_log() -> None:
                try:
                    _open_path_with_default_app(log_path)
                except FileNotFoundError:
                    ui.notify('Log file is not available yet.', type='warning')
                except OSError as exc:
                    ui.notify(f'Unable to open log file: {exc}', type='negative')
                    logger.warning('Failed to open log %s: %s', log_path, exc)

            ui.button('Open log', on_click=_open_log).props('outline')

        ui.separator()
        ui.label(
            'Calcium HTML clients call POST /api/v1/pick-and-open on this host. '
            'Quit this window to stop the server.'
        ).classes('text-caption text-grey-5')

        def _quit() -> None:
            logger.info('Quit requested from status UI')
            nicegui_app.shutdown()

        ui.button('Quit server', on_click=_quit).props('flat color=negative')
