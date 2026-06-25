"""Tests for analysis summary display helpers."""

from __future__ import annotations

import math

import numpy as np

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


def test_format_analysis_summary_lines_rounds_floats() -> None:
    summary = {
        "velocity_mean": 7.2345678,
        "velocity_cv": 10.0,
        "diameter_um_mean": np.float64(3.14159265),
    }
    text = format_analysis_summary_lines(summary)
    assert "velocity_mean: 7.235" in text
    assert "velocity_cv: 10" in text
    assert "diameter_um_mean: 3.142" in text


def test_format_analysis_summary_lines_non_finite_floats() -> None:
    summary = {"velocity_mean": math.nan, "velocity_median": math.inf}
    text = format_analysis_summary_lines(summary)
    assert "velocity_mean: nan" in text
    assert "velocity_median: inf" in text
