"""Tests for CloudScope logging helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudscope.utils import logging as logging_mod


def test_read_log_tail_raises_for_non_positive_max_lines(tmp_path: Path) -> None:
    """``read_log_tail`` should reject invalid line counts."""
    log_path = tmp_path / "cloudscope.log"
    log_path.write_text("one\n", encoding="utf-8")

    with pytest.raises(ValueError, match="max_lines must be >= 1"):
        logging_mod.read_log_tail(max_lines=0, log_path=log_path)


def test_read_log_tail_reports_disabled_file_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing file logging configuration should return a placeholder message."""
    monkeypatch.setattr(logging_mod, "get_log_file_path", lambda: None)
    assert logging_mod.read_log_tail() == logging_mod._FILE_LOGGING_DISABLED_MESSAGE


def test_read_log_tail_reports_missing_file(tmp_path: Path) -> None:
    """A configured but missing log file should return a placeholder message."""
    missing = tmp_path / "cloudscope.log"
    assert logging_mod.read_log_tail(log_path=missing) == logging_mod._LOG_FILE_MISSING_MESSAGE


def test_read_log_tail_returns_all_lines_for_small_file(tmp_path: Path) -> None:
    """Small files should return their full content."""
    log_path = tmp_path / "cloudscope.log"
    log_path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    assert logging_mod.read_log_tail(max_lines=200, log_path=log_path) == "alpha\nbeta\ngamma"


def test_read_log_tail_returns_only_last_n_lines(tmp_path: Path) -> None:
    """Large files should return only the requested trailing lines."""
    log_path = tmp_path / "cloudscope.log"
    lines = [f"line-{index}" for index in range(250)]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = logging_mod.read_log_tail(max_lines=200, log_path=log_path)

    assert result == "\n".join(lines[-200:])


def test_read_log_tail_returns_empty_string_for_empty_file(tmp_path: Path) -> None:
    """An empty log file should return an empty preview string."""
    log_path = tmp_path / "cloudscope.log"
    log_path.write_text("", encoding="utf-8")

    assert logging_mod.read_log_tail(max_lines=200, log_path=log_path) == ""


def test_attach_file_handler_to_loggers_writes_package_logs_to_cloudscope_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CloudScope file handler attachment should capture sibling package logs."""
    cloudscope_config_dir = tmp_path / "cloudscope"
    acqstore_config_dir = tmp_path / "acqstore"
    nicewidgets_config_dir = tmp_path / "nicewidgets"
    cloudscope_config_dir.mkdir()
    acqstore_config_dir.mkdir()
    nicewidgets_config_dir.mkdir()

    def _config_dir(app_name: str) -> Path:
        return {
            "cloudscope": cloudscope_config_dir,
            "acqstore": acqstore_config_dir,
            "nicewidgets": nicewidgets_config_dir,
        }[app_name]

    monkeypatch.setattr(logging_mod, "user_config_dir", _config_dir)

    from acqstore.utils.logging import get_logger as get_acqstore_logger
    from acqstore.utils.logging import setup_logging as setup_acqstore_logging
    from nicewidgets.utils.logging import get_logger as get_nicewidgets_logger
    from nicewidgets.utils.logging import setup_logging as setup_nicewidgets_logging

    logging_mod.setup_logging(level="DEBUG", app_name="cloudscope")
    setup_nicewidgets_logging(level="DEBUG", file=False, app_name="nicewidgets")
    setup_acqstore_logging(level="DEBUG", file=False, app_name="acqstore")
    logging_mod.attach_file_handler_to_loggers("acqstore", "nicewidgets")

    get_acqstore_logger("acqstore.test").info("acqstore-message")
    get_nicewidgets_logger("nicewidgets.test").info("nicewidgets-message")
    logging_mod.get_logger("cloudscope.test").info("cloudscope-message")

    log_path = cloudscope_config_dir / "logs" / "cloudscope.log"
    assert log_path.exists()
    contents = log_path.read_text(encoding="utf-8")
    assert "acqstore-message" in contents
    assert "nicewidgets-message" in contents
    assert "cloudscope-message" in contents
    assert not (acqstore_config_dir / "logs" / "acqstore.log").exists()
    assert not (nicewidgets_config_dir / "logs" / "nicewidgets.log").exists()


def test_attach_file_handler_to_loggers_noops_when_file_logging_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Attachment should do nothing when CloudScope file logging is disabled."""
    monkeypatch.setenv("CLOUDSCOPE_DISABLE_FILE_LOG", "1")
    monkeypatch.setattr(logging_mod, "user_config_dir", lambda _app_name: tmp_path)

    from acqstore.utils.logging import setup_logging as setup_acqstore_logging

    logging_mod.setup_logging(level="DEBUG", app_name="cloudscope")
    setup_acqstore_logging(level="DEBUG", file=False, app_name="acqstore")
    logging_mod.attach_file_handler_to_loggers("acqstore")

    assert logging_mod.get_log_file_path() is None
