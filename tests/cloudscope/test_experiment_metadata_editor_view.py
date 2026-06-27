"""Headless tests for ExperimentMetadataEditorView commit behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from acqstore.acq_image.acq_image_list import AcqImageList
from cloudscope.views.metadata_widget.experiment_metadata_editor_view import ExperimentMetadataEditorView


_OIR_FIXTURE = Path(__file__).resolve().parents[2] / 'tests/acqstore/data/oir-samples/20251030_A106_0004.oir'


def test_on_field_change_emits_single_field_commit() -> None:
    if not _OIR_FIXTURE.is_file():
        pytest.skip(f'Missing OIR fixture: {_OIR_FIXTURE}')
    file_list = AcqImageList(str(_OIR_FIXTURE), folder_depth=1)
    acq = file_list.get_file_by_index(0)
    received: list[tuple[str, object]] = []

    editor = ExperimentMetadataEditorView(
        on_field_commit=lambda name, value: received.append((name, value)),
        get_field_options=file_list.get_unique_metadata_values,
    )
    editor._current_acq_image = acq
    editor._on_field_change('species', 'mouse')

    assert received == [('species', 'mouse')]
    assert editor._last_committed_values['species'] == 'mouse'


def test_on_field_change_no_emit_without_record() -> None:
    received: list[tuple[str, object]] = []
    editor = ExperimentMetadataEditorView(
        on_field_commit=lambda name, value: received.append((name, value)),
    )
    editor._current_acq_image = None
    editor._on_field_change('species', 'mouse')
    assert received == []


def test_on_field_change_skips_duplicate_commit() -> None:
    if not _OIR_FIXTURE.is_file():
        pytest.skip(f'Missing OIR fixture: {_OIR_FIXTURE}')
    file_list = AcqImageList(str(_OIR_FIXTURE), folder_depth=1)
    acq = file_list.get_file_by_index(0)
    received: list[tuple[str, object]] = []

    editor = ExperimentMetadataEditorView(
        on_field_commit=lambda name, value: received.append((name, value)),
    )
    editor._current_acq_image = acq
    editor._last_committed_values['species'] = 'mouse'
    editor._on_field_change('species', 'mouse')

    assert received == []


def test_on_field_change_respects_suppression_flag() -> None:
    if not _OIR_FIXTURE.is_file():
        pytest.skip(f'Missing OIR fixture: {_OIR_FIXTURE}')
    file_list = AcqImageList(str(_OIR_FIXTURE), folder_depth=1)
    acq = file_list.get_file_by_index(0)
    received: list[tuple[str, object]] = []

    editor = ExperimentMetadataEditorView(
        on_field_commit=lambda name, value: received.append((name, value)),
    )
    editor._current_acq_image = acq
    editor._suppress_field_change = True
    editor._on_field_change('species', 'mouse')

    assert received == []
