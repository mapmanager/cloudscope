"""Logging helpers for AcqStore Server (console + rotating file + UI buffer)."""

from __future__ import annotations

import logging
import threading
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_dir

_LOGGER_NAME = 'acqstore_server'
_CONFIGURED = False
_UI_LOG_MAX_LINES = 500
_ui_log_lines: deque[str] = deque(maxlen=_UI_LOG_MAX_LINES)
_ui_log_lock = threading.Lock()
_ui_handler: logging.Handler | None = None


class _UiLogHandler(logging.Handler):
    """Append formatted log lines for the native status window."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:  # noqa: BLE001 — never break logging from UI handler
            self.handleError(record)
            return
        with _ui_log_lock:
            _ui_log_lines.append(line)


def get_ui_log_text() -> str:
    """Return the buffered UI log as a single newline-joined string.

    Returns:
        Recent log lines (newest last), capped at ``_UI_LOG_MAX_LINES``.
    """
    with _ui_log_lock:
        return '\n'.join(_ui_log_lines)


def clear_ui_log() -> None:
    """Clear the in-memory UI log buffer (tests)."""
    with _ui_log_lock:
        _ui_log_lines.clear()


def log_dir() -> Path:
    """Return the platform log directory for AcqStore Server.

    Returns:
        Directory path under the user log location (created if needed).
        On macOS this is typically ``~/Library/Logs/AcqStore Server``.
    """
    path = Path(user_log_dir(appname='AcqStore Server', appauthor='MapManager'))
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_file_path() -> Path:
    """Return the rotating log file path.

    Returns:
        ``{log_dir}/acqstore_server.log``.
    """
    return log_dir() / 'acqstore_server.log'


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under ``acqstore_server``.

    Args:
        name: Optional suffix (e.g. ``open_service``). Pass ``None`` for root.

    Returns:
        Configured logger instance.
    """
    ensure_logging()
    if name:
        return logging.getLogger(f'{_LOGGER_NAME}.{name}')
    return logging.getLogger(_LOGGER_NAME)


def ensure_logging(*, level: int = logging.INFO) -> None:
    """Configure console + rotating file handlers once.

    Args:
        level: Root logger level.
    """
    global _CONFIGURED, _ui_handler
    if _CONFIGURED:
        return

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    try:
        file_handler = RotatingFileHandler(
            log_file_path(),
            maxBytes=2_000_000,
            backupCount=5,
            encoding='utf-8',
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        file_msg = str(log_file_path())
    except OSError as exc:
        file_msg = f'(unavailable: {exc})'

    if _ui_handler is None:
        _ui_handler = _UiLogHandler()
        _ui_handler.setLevel(level)
        _ui_handler.setFormatter(formatter)
        logger.addHandler(_ui_handler)

    _CONFIGURED = True
    logger.info('Logging initialized; file=%s', file_msg)
