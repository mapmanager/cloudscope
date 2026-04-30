"""Tests for ``ApplyMetadataIntent`` / ``MetadataChanged`` controller wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from acqstore.acq_image.acq_image_list import AcqImageList
from acqstore.schema import ACQ_FILE_LIST_SCHEMA
from cloudscope.core.home_page_controller import HomePageController
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import ApplyMetadataIntent, MetadataChanged

_OIR_FIXTURE = Path(__file__).resolve().parents[2] / 'tests/acqstore/data/oir-samples/20251030_A106_0004.oir'


def test_apply_metadata_intent_updates_experiment_metadata_and_emits_state() -> None:
    if not _OIR_FIXTURE.is_file():
        pytest.skip(f'Missing OIR fixture: {_OIR_FIXTURE}')
    lst = AcqImageList(str(_OIR_FIXTURE), folder_depth=1)
    acq = lst.get_file_by_index(0)

    bus = EventBus()
    ctrl = HomePageController(event_bus=bus)
    ctrl.bind()
    ctrl.load_acq_image_list(lst)

    seen: list[MetadataChanged] = []
    bus.subscribe(MetadataChanged, lambda e: seen.append(e))

    fid = acq.file_id
    bus.publish(
        ApplyMetadataIntent(
            file_id=fid,
            metadata_section_id='experiment_metadata',
            patch={'species': 'mouse'},
        )
    )

    exp = acq.get_metadata_section('experiment_metadata')
    assert exp.get_values()['species'] == 'mouse'
    assert len(seen) == 1
    ev = seen[0]
    assert ev.file_id == fid
    assert ev.metadata_section_id == 'experiment_metadata'
    assert isinstance(ev.file_list_row, dict)
    assert tuple(ev.file_list_row.keys()) == ACQ_FILE_LIST_SCHEMA.field_names()
    assert ev.file_list_row['name'] == Path(fid).name


def test_apply_metadata_unknown_section_raises_with_list() -> None:
    if not _OIR_FIXTURE.is_file():
        pytest.skip(f'Missing OIR fixture: {_OIR_FIXTURE}')
    lst = AcqImageList(str(_OIR_FIXTURE), folder_depth=1)
    bus = EventBus()
    ctrl = HomePageController(event_bus=bus)
    ctrl.bind()
    ctrl.load_acq_image_list(lst)
    fid = lst.get_file_by_index(0).file_id
    with pytest.raises(ValueError, match='Unknown metadata section'):
        bus.publish(
            ApplyMetadataIntent(
                file_id=fid,
                metadata_section_id='wrong_section',  # type: ignore[arg-type]
                patch={'species': 'x'},
            )
        )


def test_apply_metadata_without_list_raises() -> None:
    bus = EventBus()
    ctrl = HomePageController(event_bus=bus)
    ctrl.bind()
    ctrl.load_demo_files(['a'])
    with pytest.raises(RuntimeError, match='AcqImageList'):
        bus.publish(
            ApplyMetadataIntent(
                file_id='a',
                metadata_section_id='experiment_metadata',
                patch={'species': 'x'},
            )
        )
