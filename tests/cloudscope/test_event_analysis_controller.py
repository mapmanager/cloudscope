"""Tests for event-analysis controller dependency enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.controllers.event_analysis_controller import EventAnalysisController
from cloudscope.event_bus import EventBus
from cloudscope.events.status import AppStatusChanged, StatusLevel
from cloudscope.state import PrimarySelection


@dataclass
class DummyState:
    """Minimal home-controller state for event-controller tests."""

    selection: PrimarySelection
    acq_image_list: object | None = None


@dataclass
class DummyHomeController:
    """Minimal home controller exposing ``state``."""

    state: DummyState


def test_begin_event_edit_requires_radon_velocity_dependency() -> None:
    """The controller should block event editing when Radon is missing."""
    bus = EventBus()
    statuses: list[AppStatusChanged] = []
    bus.subscribe(AppStatusChanged, statuses.append)
    controller = EventAnalysisController(
        event_bus=bus,
        home_controller=DummyHomeController(
            DummyState(
                selection=PrimarySelection(file_id="file-1", channel=0, roi_id=1),
                acq_image_list=None,
            )
        ),
    )

    allowed = controller._can_begin_edit_mode(PrimarySelection(file_id="file-1", channel=0, roi_id=1))

    assert allowed is False
    assert statuses[-1].level is StatusLevel.WARNING
    assert "No AcqImageList loaded" in statuses[-1].message
