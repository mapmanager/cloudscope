"""Minimal NiceGUI status window for AcqStore Server (server's own UI)."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import subprocess
import urllib.request
import webbrowser
from pathlib import Path

from nicegui import app as nicegui_app
from nicegui import ui

from acqstore_server.gui_defaults import setUpGuiDefaults
from acqstore_server.logging_setup import get_logger, get_ui_log_text, log_file_path
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
    setUpGuiDefaults('text-xs')

    base = f'http://{host}:{port}'
    log_path = log_file_path()

    ui.colors(primary='#38bdf8')

    with ui.column().classes('w-full h-full p-3 gap-2'):
        ui.label('AcqStore Server').classes('text-h6 text-primary')

        with ui.row().classes('gap-2 flex-wrap'):
            ui.button(
                'Open demo',
                on_click=lambda: webbrowser.open(f'{base}/demo/v2/'),
            ).props('color=primary')
            ui.button(
                'API docs (/docs)',
                on_click=lambda: webbrowser.open(f'{base}/docs'),
            ).props('outline')

            async def _show_health() -> None:
                url = f'{base}/api/v2/health'
                try:
                    def _fetch() -> str:
                        with urllib.request.urlopen(url, timeout=5) as resp:
                            return resp.read().decode('utf-8')

                    raw = await asyncio.to_thread(_fetch)
                    try:
                        text = json.dumps(json.loads(raw), indent=2)
                    except json.JSONDecodeError:
                        text = raw
                    logger.info('Health %s\n%s', url, text)
                except Exception as exc:  # noqa: BLE001
                    logger.warning('Health request failed: %s — %s', url, exc)
                    ui.notify(f'Health request failed: {exc}', type='negative')

            ui.button('Show health', on_click=_show_health).props('outline')

            def _open_log() -> None:
                try:
                    _open_path_with_default_app(log_path)
                except FileNotFoundError:
                    ui.notify('Log file is not available yet.', type='warning')
                except OSError as exc:
                    ui.notify(f'Unable to open log file: {exc}', type='negative')
                    logger.warning('Failed to open log %s: %s', log_path, exc)

            ui.button('Open log', on_click=_open_log).props('outline')

            def _quit() -> None:
                logger.info('Quit requested from status UI')
                nicegui_app.shutdown()

            ui.button('Quit server', on_click=_quit).props('flat color=negative')

        ui.label('Server log').classes('text-caption text-grey-5')
        with ui.scroll_area().classes('w-full border rounded').style('height: 360px'):
            log_view = (
                ui.label(get_ui_log_text())
                .classes('w-full font-mono whitespace-pre-wrap text-xs select-text')
            )

        def _refresh_log() -> None:
            text = get_ui_log_text()
            if log_view.text != text:
                log_view.set_text(text)

        ui.timer(0.5, _refresh_log)

    with ui.footer().classes('bg-grey-10 text-grey-4 q-px-md q-py-xs'):
        ui.label(f'{APP_NAME} v{APP_VERSION}  ·  {host}:{port}').classes('text-caption')
