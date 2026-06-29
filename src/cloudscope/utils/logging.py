"""Logging utilities for CloudScope.

Application entry points should call :func:`setup_logging` once at startup.
Library/module code should call :func:`get_logger`.

Example:
    from cloudscope.utils.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Loaded file")
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "cloudscope"
DEFAULT_LOG_FILENAME = "cloudscope.log"
DISABLE_FILE_LOG_ENV = "CLOUDSCOPE_DISABLE_FILE_LOG"

_LOG_FILE_PATH: Path | None = None
_FILE_HANDLER: logging.Handler | None = None
_ATTACHED_PACKAGE_LOGGERS: set[str] = set()
_HANDLER_MARKER = "_cloudscope_handler"


def setup_logging(
    level: str | int = "INFO",
    *,
    app_name: str = APP_NAME,
    log_filename: str = DEFAULT_LOG_FILENAME,
    console: bool = True,
    file: bool = True,
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> None:
    """Configure CloudScope package logging.

    This configures the ``cloudscope`` logger rather than the Python root logger.
    Calling this function more than once replaces handlers previously installed
    by this function.

    Args:
        level: Console logging level. May be a string such as ``"INFO"`` or a
            standard logging integer such as ``logging.INFO``.
        app_name: Application name used by ``platformdirs`` for the log folder.
        log_filename: Name of the log file.
        console: If True, write logs to stderr.
        file: If True, write logs to a rotating file.
        max_bytes: Maximum size of the log file before rotation.
        backup_count: Number of rotated log files to keep.

    Returns:
        None.
    """
    resolved_level = _resolve_level(level)

    global _LOG_FILE_PATH

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    _remove_cloudscope_handlers(logger)

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(resolved_level)
        console_handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: %(message)s")
        )
        setattr(console_handler, _HANDLER_MARKER, True)
        logger.addHandler(console_handler)

    if file and not _file_log_disabled():
        global _LOG_FILE_PATH, _FILE_HANDLER
        log_dir = Path(user_config_dir(app_name)) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        _LOG_FILE_PATH = log_dir / log_filename

        file_handler = logging.handlers.RotatingFileHandler(
            filename=_LOG_FILE_PATH,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        setattr(file_handler, _HANDLER_MARKER, True)
        _FILE_HANDLER = file_handler
        logger.addHandler(file_handler)
    else:
        _LOG_FILE_PATH = None


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a CloudScope logger.

    Args:
        name: Logger name. Pass ``__name__`` from calling modules. If None,
            returns the top-level ``cloudscope`` logger.

    Returns:
        A standard Python logger.
    """
    return logging.getLogger(name or APP_NAME)


def get_log_file_path() -> Path | None:
    """Return the active log file path.

    Returns:
        Path to the CloudScope log file if file logging has been configured,
        otherwise None.
    """
    return _LOG_FILE_PATH


def attach_file_handler_to_loggers(*logger_names: str) -> None:
    """Attach the active CloudScope file handler to other package loggers.

    CloudScope application entry points should call this after
    :func:`setup_logging` and after sibling packages call their own
    ``setup_logging(..., file=False)`` so library logs are written to
    ``cloudscope.log`` without creating separate package log files.

    Args:
        logger_names: Package-root logger names such as ``"acqstore"`` and
            ``"nicewidgets"``.

    Returns:
        None.
    """
    if _FILE_HANDLER is None:
        return

    for logger_name in logger_names:
        package_logger = logging.getLogger(logger_name)
        if _FILE_HANDLER not in package_logger.handlers:
            package_logger.addHandler(_FILE_HANDLER)
        _ATTACHED_PACKAGE_LOGGERS.add(logger_name)


_FILE_LOGGING_DISABLED_MESSAGE = "File logging is not enabled."
_LOG_FILE_MISSING_MESSAGE = "Log file is not available yet."


def read_log_tail(*, max_lines: int = 200, log_path: Path | None = None) -> str:
    """Read the last lines from the CloudScope log file.

    Args:
        max_lines: Maximum number of lines to return from the end of the file.
        log_path: Optional path override used by tests. When ``None``, uses
            :func:`get_log_file_path`.

    Returns:
        Log text, an empty string when the file exists but has no lines, or a
        short placeholder message when file logging is unavailable.

    Raises:
        ValueError: If ``max_lines`` is less than 1.
    """
    if max_lines < 1:
        raise ValueError(f"max_lines must be >= 1, got {max_lines}")

    path = log_path if log_path is not None else get_log_file_path()
    if path is None:
        return _FILE_LOGGING_DISABLED_MESSAGE
    if not path.exists():
        return _LOG_FILE_MISSING_MESSAGE

    try:
        return _read_tail_lines(path, max_lines)
    except OSError as exc:
        get_logger(__name__).warning("Failed to read log tail from %s", path, exc_info=True)
        return f"Unable to read log file: {exc}"


def _read_tail_lines(path: Path, max_lines: int) -> str:
    """Return up to ``max_lines`` lines from the end of a text file.

    Args:
        path: Log file path.
        max_lines: Maximum number of trailing lines to return.

    Returns:
        Trailing file content without a trailing newline unless the source file
        ends with one and the final returned line is incomplete relative to the
        requested tail window.
    """
    chunk_size = 8192
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        file_size = handle.tell()
        if file_size == 0:
            return ""

        buffer = b""
        position = file_size
        line_count = 0
        while position > 0 and line_count <= max_lines:
            read_size = min(chunk_size, position)
            position -= read_size
            handle.seek(position)
            buffer = handle.read(read_size) + buffer
            line_count = buffer.count(b"\n")

    text = buffer.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def _resolve_level(level: str | int) -> int:
    """Resolve a logging level from a string or integer.

    Args:
        level: Logging level as a string (e.g. "INFO") or integer.

    Returns:
        Integer logging level.

    Raises:
        ValueError: If a string level is not recognized.
        TypeError: If level is not str or int.
    """
    if isinstance(level, int):
        return level

    if not isinstance(level, str):
        raise TypeError(f"Invalid level type: {type(level)}")

    level_upper = level.upper()

    try:
        return logging._nameToLevel[level_upper]
    except KeyError:
        raise ValueError(f"Unknown logging level: {level!r}") from None

def _remove_cloudscope_handlers(logger: logging.Logger) -> None:
    """Remove handlers previously installed by ``setup_logging``.

    Args:
        logger: Logger to clean.

    Returns:
        None.
    """
    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            logger.removeHandler(handler)
            _detach_shared_file_handler(handler)
            handler.close()


def _detach_shared_file_handler(handler: logging.Handler) -> None:
    """Remove a shared CloudScope file handler from attached package loggers.

    Args:
        handler: Handler being removed from the CloudScope logger.

    Returns:
        None.
    """
    global _FILE_HANDLER
    if handler is not _FILE_HANDLER:
        return
    for logger_name in list(_ATTACHED_PACKAGE_LOGGERS):
        logging.getLogger(logger_name).removeHandler(handler)
    _ATTACHED_PACKAGE_LOGGERS.clear()
    _FILE_HANDLER = None


def _file_log_disabled() -> bool:
    """Return whether file logging is disabled by environment variable.

    Returns:
        True if ``CLOUDSCOPE_DISABLE_FILE_LOG`` is set to a truthy value.
    """
    value = os.getenv(DISABLE_FILE_LOG_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}