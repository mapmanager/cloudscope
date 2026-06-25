"""Tests for analysis summary display helpers."""

from __future__ import annotations

from cloudscope.views.analysis_summary_display import format_analysis_summary_lines


def test_format_analysis_summary_lines_metadata_first() -> None:
    summary = {
        "velocity_mean": 7.2,
        "analysis_time": "14:32:07.042",
        "num_windows": 10,
        "analysis_date": "260623",
        "analysis_version": 1,
    }
    text = format_analysis_summary_lines(summary)
    lines = text.splitlines()
    assert lines[0] == "analysis_date: 260623"
    assert lines[1] == "analysis_time: 14:32:07.042"
    assert lines[2] == "analysis_version: 1"
    assert "velocity_mean: 7.2" in lines
    assert "num_windows: 10" in lines


def test_format_analysis_summary_lines_empty_dict() -> None:
    assert format_analysis_summary_lines({}) == ""
