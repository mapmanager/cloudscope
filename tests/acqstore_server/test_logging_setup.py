"""Tests for AcqStore Server logging helpers."""

from __future__ import annotations

from acqstore_server.logging_setup import (
    clear_ui_log,
    get_logger,
    get_ui_log_text,
    log_dir,
    log_file_path,
)


def test_log_paths_under_acqstore_server_name() -> None:
    directory = log_dir()
    assert directory.is_dir()
    assert 'AcqStore Server' in str(directory) or 'acqstore' in str(directory).lower()
    assert log_file_path().name == 'acqstore_server.log'


def test_get_logger_logs_without_error() -> None:
    logger = get_logger('test')
    logger.info('unit test log line')


def test_ui_log_buffer_receives_logger_lines() -> None:
    clear_ui_log()
    logger = get_logger('ui_buffer_test')
    marker = 'ui-log-buffer-marker-xyz'
    logger.info(marker)
    text = get_ui_log_text()
    assert marker in text
