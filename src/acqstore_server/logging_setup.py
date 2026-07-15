"""Logging helpers for AcqStore Server (console + rotating file)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_dir

_LOGGER_NAME = 'acqstore_server'
_CONFIGURED = False


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
    global _CONFIGURED
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

    _CONFIGURED = True
    logger.info('Logging initialized; file=%s', file_msg)
