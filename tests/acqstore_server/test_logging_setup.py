"""Tests for AcqStore Server logging helpers."""

from __future__ import annotations

from acqstore_server.logging_setup import get_logger, log_dir, log_file_path


def test_log_paths_under_acqstore_server_name() -> None:
    directory = log_dir()
    assert directory.is_dir()
    assert 'AcqStore Server' in str(directory) or 'acqstore' in str(directory).lower()
    assert log_file_path().name == 'acqstore_server.log'


def test_get_logger_logs_without_error() -> None:
    logger = get_logger('test')
    logger.info('unit test log line')
