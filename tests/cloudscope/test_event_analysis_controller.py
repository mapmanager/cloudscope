"""Tests for EventAnalysisController."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acqstore.acq_image.analysis.event_analysis.event_analysis import (
    EventAnalysis,
    EventType,
)
from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisPlotData
from cloudscope.controllers.event_analysis_controller import EventAnalysisController
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
    AcqImageEventXRangeSelectedIntent,
    BeginAddAcqImageEventIntent,
    BeginEditAcqImageEventIntent,
    CancelAddAcqImageEventIntent,
    DeleteSelectedAcqImageEventIntent,
    EventEditMode,
    RequestAcqImageEventsRefreshIntent,
    SelectAcqImageEventIntent,
    SetAcqImageEventsVisibleIntent,
)
from cloudscope.events.analysis import (
    AppBusyChanged,
    BeginPlotXRangeSelection,
    CancelPlotXRangeSelection,
)
from cloudscope.events.selection import FileSelectionChanged
from cloudscope.events.status import AppStatusChanged, StatusLevel
from cloudscope.state import PrimarySelection


# ---- Fakes ----


@dataclass
class FakeState:
    """Minimal home-controller state."""

    selection: PrimarySelection
    acq_image_list: object | None = None


@dataclass
class FakeHomeController:
    """Minimal home controller exposing ``state``."""

    state: FakeState


class FakeRadon:
    """Stand-in for a Radon analysis exposing get_plot_data()."""

    def __init__(self, plot_data: AnalysisPlotData | None) -> None:
        self._plot_data = plot_data

    def get_plot_data(self) -> AnalysisPlotData | None:
        return self._plot_data


class FakeAnalysisSet:
    """Stand-in for AcqAnalysisSet exposing the methods used by the controller."""

    def __init__(self) -> None:
        self._items: dict[AnalysisKey, Any] = {}
        self.created: list[tuple[str, int, int]] = []

    def get(self, key: AnalysisKey) -> Any:
        return self._items.get(key)

    def set(self, key: AnalysisKey, analysis: Any) -> None:
        self._items[key] = analysis

    def get_or_create(
        self,
        analysis_name: str,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, Any] | None = None,
    ) -> Any:
        key = AnalysisKey(analysis_name, channel, roi_id)
        if key not in self._items:
            self.created.append((analysis_name, channel, roi_id))
            if analysis_name == "event":
                self._items[key] = EventAnalysis(channel=channel, roi_id=roi_id)
        return self._items.get(key)


class FakeAcqImage:
    def __init__(self, analysis_set: FakeAnalysisSet | None = None) -> None:
        self.analysis_set = analysis_set or FakeAnalysisSet()


class FakeAcqImageList:
    def __init__(self, acq_image: FakeAcqImage | None) -> None:
        self._image = acq_image

    def get_file_by_id(self, file_id: str) -> FakeAcqImage | None:
        _ = file_id
        return self._image


@dataclass
class Capture:
    """Container for bus subscriptions captured during a test."""

    statuses: list[AppStatusChanged] = field(default_factory=list)
    events_changed: list[AcqImageEventsChanged] = field(default_factory=list)
    event_selections: list[AcqImageEventSelectionChanged] = field(default_factory=list)
    busy: list[AppBusyChanged] = field(default_factory=list)
    begin_x: list[BeginPlotXRangeSelection] = field(default_factory=list)
    cancel_x: list[CancelPlotXRangeSelection] = field(default_factory=list)


def _make(
    *,
    selection: PrimarySelection | None = None,
    acq_image: FakeAcqImage | None | object = ...,
    plot_data: AnalysisPlotData | None = None,
    seed_event_analysis: bool = False,
) -> tuple[EventAnalysisController, EventBus, Capture, FakeHomeController]:
    """Build a wired controller with bus subscriptions captured."""
    bus = EventBus()
    cap = Capture()
    bus.subscribe(AppStatusChanged, cap.statuses.append)
    bus.subscribe(AcqImageEventsChanged, cap.events_changed.append)
    bus.subscribe(AcqImageEventSelectionChanged, cap.event_selections.append)
    bus.subscribe(AppBusyChanged, cap.busy.append)
    bus.subscribe(BeginPlotXRangeSelection, cap.begin_x.append)
    bus.subscribe(CancelPlotXRangeSelection, cap.cancel_x.append)

    sel = selection or PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    if acq_image is ...:
        aset = FakeAnalysisSet()
        if plot_data is not None:
            aset.set(AnalysisKey("radon_velocity", 0, 1), FakeRadon(plot_data))
        if seed_event_analysis:
            aset.set(AnalysisKey("event", 0, 1), EventAnalysis(channel=0, roi_id=1))
        img: FakeAcqImage | None = FakeAcqImage(aset)
        acq_list: FakeAcqImageList | None = FakeAcqImageList(img)
    elif acq_image is None:
        acq_list = None
    else:
        acq_list = FakeAcqImageList(acq_image)  # type: ignore[arg-type]

    home = FakeHomeController(FakeState(selection=sel, acq_image_list=acq_list))
    controller = EventAnalysisController(event_bus=bus, home_controller=home)  # type: ignore[arg-type]
    controller.bind()
    return controller, bus, cap, home


def _plot_data() -> AnalysisPlotData:
    return AnalysisPlotData(
        x=tuple(float(i) for i in range(20)),
        y=tuple(float(i) for i in range(20)),
        x_label="Time (s)",
        y_label="Velocity",
        series_name="Radon velocity",
    )


# ---- _can_begin_edit_mode / status guards ----


def test_begin_event_edit_requires_radon_velocity_dependency() -> None:
    """The controller should block event editing when AcqImageList is missing."""
    controller, _, cap, _ = _make(acq_image=None)

    allowed = controller._can_begin_edit_mode(
        PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    )

    assert allowed is False
    assert cap.statuses[-1].level is StatusLevel.WARNING
    assert "No AcqImageList loaded" in cap.statuses[-1].message


def test_begin_event_edit_requires_existing_radon_analysis() -> None:
    """Edit should fail with helpful status when Radon analysis is absent."""
    controller, _, cap, _ = _make(plot_data=None)

    allowed = controller._can_begin_edit_mode(
        PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    )

    assert allowed is False
    assert "Run Radon velocity analysis" in cap.statuses[-1].message


def test_begin_event_edit_requires_complete_selection() -> None:
    """Edit should fail with helpful status when selection is incomplete."""
    controller, _, cap, _ = _make(plot_data=_plot_data())

    assert controller._can_begin_edit_mode(PrimarySelection()) is False
    assert "file" in cap.statuses[-1].message.lower()


def test_begin_event_edit_rejects_while_already_in_edit_mode() -> None:
    """Entering edit mode twice should be guarded."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    bus.publish(
        BeginAddAcqImageEventIntent(
            selection=PrimarySelection(file_id="file-1", channel=0, roi_id=1),
        )
    )
    cap.statuses.clear()

    assert controller._edit_mode is EventEditMode.ADD
    assert (
        controller._can_begin_edit_mode(
            PrimarySelection(file_id="file-1", channel=0, roi_id=1)
        )
        is False
    )
    assert "Finish or cancel" in cap.statuses[-1].message


# ---- _on_begin_add ----


def test_begin_add_enters_add_mode_and_publishes_busy_and_begin_x() -> None:
    """Begin-add should publish AppBusy, BeginPlotXRangeSelection, and AcqImageEventsChanged."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)

    bus.publish(BeginAddAcqImageEventIntent(selection=sel))

    assert controller._edit_mode is EventEditMode.ADD
    assert any(b.is_busy is True for b in cap.busy)
    assert cap.begin_x and cap.begin_x[-1].selection == sel
    assert cap.events_changed
    assert cap.events_changed[-1].edit_mode is EventEditMode.ADD


# ---- _on_begin_edit ----


def test_begin_edit_warns_when_no_event_selected() -> None:
    """Begin-edit should fail with a warning when no event is selected."""
    controller, bus, cap, _ = _make(plot_data=_plot_data(), seed_event_analysis=True)
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    cap.statuses.clear()

    bus.publish(BeginEditAcqImageEventIntent(selection=sel))

    assert controller._edit_mode is EventEditMode.NONE
    assert cap.statuses[-1].level is StatusLevel.WARNING
    assert "No event selected" in cap.statuses[-1].message


def test_begin_edit_warns_when_no_event_analysis() -> None:
    """Begin-edit should fail when the event analysis does not exist yet."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    controller.selected_event_id = 7
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)

    bus.publish(BeginEditAcqImageEventIntent(selection=sel))

    assert controller._edit_mode is EventEditMode.NONE
    assert "No event analysis" in cap.statuses[-1].message


def test_begin_edit_clears_selection_when_event_id_missing() -> None:
    """Begin-edit should clear stale event id when it no longer exists."""
    controller, bus, cap, _ = _make(plot_data=_plot_data(), seed_event_analysis=True)
    controller.selected_event_id = 9999
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)

    bus.publish(BeginEditAcqImageEventIntent(selection=sel))

    assert controller.selected_event_id is None
    assert any(e.selected_event_id is None for e in cap.event_selections)
    assert "no longer exists" in cap.statuses[-1].message


def test_begin_edit_enters_edit_mode_when_event_exists() -> None:
    """Begin-edit should enter EDIT mode when the selected event exists."""
    controller, bus, cap, home = _make(plot_data=_plot_data(), seed_event_analysis=True)
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    analysis = home.state.acq_image_list._image.analysis_set._items[  # type: ignore[union-attr]
        AnalysisKey("event", 0, 1)
    ]
    created = analysis.add_event(2.0, 5.0, plot_data=_plot_data())
    controller.selected_event_id = int(created.id)

    bus.publish(BeginEditAcqImageEventIntent(selection=sel))

    assert controller._edit_mode is EventEditMode.EDIT
    assert cap.begin_x


# ---- _on_cancel_edit ----


def test_cancel_when_not_editing_is_noop() -> None:
    """Cancel intent issued while idle should produce no events."""
    _, bus, cap, _ = _make(plot_data=_plot_data())

    bus.publish(CancelAddAcqImageEventIntent())

    assert cap.busy == []
    assert cap.cancel_x == []
    assert cap.events_changed == []


def test_cancel_while_editing_clears_mode_and_publishes_cancel_x() -> None:
    """Cancel while in edit mode should leave mode and publish CancelPlotXRangeSelection."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    bus.publish(
        BeginAddAcqImageEventIntent(
            selection=PrimarySelection(file_id="file-1", channel=0, roi_id=1),
        )
    )
    cap.cancel_x.clear()
    cap.events_changed.clear()

    bus.publish(CancelAddAcqImageEventIntent())

    assert controller._edit_mode is EventEditMode.NONE
    assert cap.cancel_x
    assert cap.events_changed


# ---- _on_x_range_selected ----


def test_x_range_selected_ignored_when_not_in_edit_mode() -> None:
    """Range selection should be ignored when no edit is pending."""
    _, bus, cap, _ = _make(plot_data=_plot_data())
    bus.publish(
        AcqImageEventXRangeSelectedIntent(
            selection=PrimarySelection(file_id="file-1", channel=0, roi_id=1),
            x0=1.0,
            x1=2.0,
        )
    )

    assert cap.events_changed == []


def test_x_range_selected_ignores_stale_selection() -> None:
    """A range for a different selection should be ignored while editing."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    bus.publish(
        BeginAddAcqImageEventIntent(
            selection=PrimarySelection(file_id="file-1", channel=0, roi_id=1),
        )
    )
    cap.events_changed.clear()

    bus.publish(
        AcqImageEventXRangeSelectedIntent(
            selection=PrimarySelection(file_id="file-1", channel=0, roi_id=2),
            x0=1.0,
            x1=2.0,
        )
    )

    assert controller._edit_mode is EventEditMode.ADD
    assert cap.events_changed == []


def test_x_range_selected_adds_event_in_add_mode() -> None:
    """ADD mode should create a new event with the picked x0/x1."""
    controller, bus, cap, home = _make(plot_data=_plot_data())
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    bus.publish(BeginAddAcqImageEventIntent(selection=sel))

    bus.publish(AcqImageEventXRangeSelectedIntent(selection=sel, x0=3.0, x1=6.0))

    assert controller._edit_mode is EventEditMode.NONE
    aset = home.state.acq_image_list._image.analysis_set  # type: ignore[union-attr]
    event_analysis = aset.get(AnalysisKey("event", 0, 1))
    events = event_analysis.get_events()
    assert len(events) == 1
    assert events[0].x0 == 3.0 and events[0].x1 == 6.0
    assert controller.selected_event_id == int(events[0].id)
    assert any(e.selected_event_id == int(events[0].id) for e in cap.event_selections)


def test_x_range_selected_updates_event_in_edit_mode() -> None:
    """EDIT mode should update coordinates of the selected event."""
    controller, bus, cap, home = _make(plot_data=_plot_data(), seed_event_analysis=True)
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    analysis = home.state.acq_image_list._image.analysis_set._items[  # type: ignore[union-attr]
        AnalysisKey("event", 0, 1)
    ]
    created = analysis.add_event(1.0, 2.0, plot_data=_plot_data())
    controller.selected_event_id = int(created.id)
    bus.publish(BeginEditAcqImageEventIntent(selection=sel))

    bus.publish(AcqImageEventXRangeSelectedIntent(selection=sel, x0=4.0, x1=8.0))

    updated = analysis.events.get_required(int(created.id))
    assert updated.x0 == 4.0 and updated.x1 == 8.0
    assert controller._edit_mode is EventEditMode.NONE


def test_x_range_selected_error_clears_edit_and_publishes_status() -> None:
    """A failure mid-update should publish an error status and clear edit mode."""
    controller, bus, cap, home = _make(plot_data=_plot_data(), seed_event_analysis=True)
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    controller.selected_event_id = None
    controller._edit_mode = EventEditMode.EDIT
    controller._pending_selection = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    cap.statuses.clear()

    bus.publish(AcqImageEventXRangeSelectedIntent(selection=sel, x0=1.0, x1=2.0))

    assert controller._edit_mode is EventEditMode.NONE
    assert any(s.level is StatusLevel.ERROR for s in cap.statuses)
    assert cap.cancel_x


# ---- _on_delete_selected ----


def test_delete_selected_warns_when_no_event_selected() -> None:
    """Delete should warn when no event id is selected."""
    _, bus, cap, _ = _make(plot_data=_plot_data(), seed_event_analysis=True)
    cap.statuses.clear()

    bus.publish(DeleteSelectedAcqImageEventIntent())

    assert cap.statuses
    assert cap.statuses[-1].level is StatusLevel.WARNING
    assert "No event selected" in cap.statuses[-1].message


def test_delete_selected_blocked_while_editing() -> None:
    """Delete should be blocked while in edit mode."""
    controller, bus, cap, _ = _make(plot_data=_plot_data(), seed_event_analysis=True)
    controller.selected_event_id = 1
    controller._edit_mode = EventEditMode.ADD

    bus.publish(DeleteSelectedAcqImageEventIntent())

    assert "Cancel event editing" in cap.statuses[-1].message
    assert controller.selected_event_id == 1


def test_delete_selected_removes_event() -> None:
    """Delete should remove the event and clear selection."""
    controller, bus, cap, home = _make(plot_data=_plot_data(), seed_event_analysis=True)
    analysis = home.state.acq_image_list._image.analysis_set._items[  # type: ignore[union-attr]
        AnalysisKey("event", 0, 1)
    ]
    created = analysis.add_event(1.0, 2.0, plot_data=_plot_data())
    controller.selected_event_id = int(created.id)

    bus.publish(DeleteSelectedAcqImageEventIntent())

    assert controller.selected_event_id is None
    assert analysis.get_events() == []
    assert any(e.selected_event_id is None for e in cap.event_selections)


def test_delete_selected_returns_when_event_analysis_missing() -> None:
    """Delete should silently return if there's no event analysis to delete from."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    controller.selected_event_id = 1
    cap.events_changed.clear()
    cap.event_selections.clear()

    bus.publish(DeleteSelectedAcqImageEventIntent())

    assert controller.selected_event_id == 1
    assert cap.event_selections == []


def test_delete_selected_publishes_error_on_failure() -> None:
    """Delete error should publish an ERROR status."""
    controller, bus, cap, _ = _make(plot_data=_plot_data(), seed_event_analysis=True)
    controller.selected_event_id = 9999
    cap.statuses.clear()

    bus.publish(DeleteSelectedAcqImageEventIntent())

    assert any(s.level is StatusLevel.ERROR for s in cap.statuses)


# ---- _on_select_event ----


def test_select_event_sets_id_and_publishes_selection_change() -> None:
    """Select should update the id and publish a selection change."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())

    bus.publish(SelectAcqImageEventIntent(event_id=42))

    assert controller.selected_event_id == 42
    assert cap.event_selections[-1].selected_event_id == 42


def test_select_event_clears_when_none() -> None:
    """Select with None should clear the selection."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    controller.selected_event_id = 5

    bus.publish(SelectAcqImageEventIntent(event_id=None))

    assert controller.selected_event_id is None
    assert cap.event_selections[-1].selected_event_id is None


def test_select_event_ignored_during_edit_mode() -> None:
    """Selection changes should be suppressed during edit mode."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    controller._edit_mode = EventEditMode.EDIT

    bus.publish(SelectAcqImageEventIntent(event_id=42))

    assert controller.selected_event_id is None
    assert cap.event_selections == []


# ---- _on_set_visible ----


def test_set_visible_updates_flag_and_publishes_events_changed() -> None:
    """Visibility intent should update the flag and republish event state."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    cap.events_changed.clear()

    bus.publish(SetAcqImageEventsVisibleIntent(visible=False))

    assert controller.events_visible is False
    assert cap.events_changed and cap.events_changed[-1].visible is False


# ---- _on_refresh_requested ----


def test_refresh_requested_publishes_rows_for_selection() -> None:
    """Refresh intent should publish rows for the requested selection."""
    _, bus, cap, home = _make(plot_data=_plot_data(), seed_event_analysis=True)
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    analysis = home.state.acq_image_list._image.analysis_set._items[  # type: ignore[union-attr]
        AnalysisKey("event", 0, 1)
    ]
    analysis.add_event(1.0, 2.0, plot_data=_plot_data())
    cap.events_changed.clear()

    bus.publish(RequestAcqImageEventsRefreshIntent(selection=sel))

    assert len(cap.events_changed) == 1
    assert len(cap.events_changed[-1].rows) == 1


def test_refresh_requested_publishes_empty_rows_when_no_analysis() -> None:
    """Refresh should publish empty rows when no event analysis exists."""
    _, bus, cap, _ = _make(plot_data=_plot_data())
    sel = PrimarySelection(file_id="file-1", channel=0, roi_id=1)
    cap.events_changed.clear()

    bus.publish(RequestAcqImageEventsRefreshIntent(selection=sel))

    assert cap.events_changed
    assert cap.events_changed[-1].rows == []


# ---- _on_primary_selection_changed ----


def test_primary_selection_changed_clears_selection_and_publishes_rows() -> None:
    """Selection change should clear selected event id and publish rows."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    controller.selected_event_id = 7

    bus.publish(FileSelectionChanged(file_id="x", acq_image=None, channel=0, roi_id=1))

    assert controller.selected_event_id is None
    assert any(e.selected_event_id is None for e in cap.event_selections)
    assert cap.events_changed


def test_primary_selection_changed_clears_edit_mode() -> None:
    """Selection change should cancel any pending edit and publish CancelPlotXRangeSelection."""
    controller, bus, cap, _ = _make(plot_data=_plot_data())
    bus.publish(
        BeginAddAcqImageEventIntent(
            selection=PrimarySelection(file_id="file-1", channel=0, roi_id=1),
        )
    )
    cap.cancel_x.clear()
    cap.busy.clear()

    bus.publish(
        FileSelectionChanged(file_id="other", acq_image=None, channel=0, roi_id=1)
    )

    assert controller._edit_mode is EventEditMode.NONE
    assert cap.cancel_x
    assert any(b.is_busy is False for b in cap.busy)


# ---- helpers ----


def test_required_selection_values_raises_on_missing_fields() -> None:
    """Static helper should fail-fast on missing fields."""
    import pytest

    with pytest.raises(ValueError, match="file"):
        EventAnalysisController._required_selection_values(PrimarySelection())
    with pytest.raises(ValueError, match="channel"):
        EventAnalysisController._required_selection_values(
            PrimarySelection(file_id="f")
        )
    with pytest.raises(ValueError, match="ROI"):
        EventAnalysisController._required_selection_values(
            PrimarySelection(file_id="f", channel=0)
        )


def test_copy_selection_returns_independent_instance() -> None:
    """_copy_selection should return a structurally equal but distinct instance."""
    sel = PrimarySelection(file_id="f", channel=1, roi_id=2)
    copy = EventAnalysisController._copy_selection(sel)
    assert copy == sel
    assert copy is not sel


def test_same_selection_compares_all_three_fields() -> None:
    """_same_selection should require all three fields to match."""
    a = PrimarySelection(file_id="f", channel=0, roi_id=1)
    assert EventAnalysisController._same_selection(a, PrimarySelection(file_id="f", channel=0, roi_id=1))
    assert not EventAnalysisController._same_selection(a, PrimarySelection(file_id="g", channel=0, roi_id=1))
    assert not EventAnalysisController._same_selection(a, PrimarySelection(file_id="f", channel=1, roi_id=1))
    assert not EventAnalysisController._same_selection(a, PrimarySelection(file_id="f", channel=0, roi_id=2))


def test_event_row_contains_expected_keys() -> None:
    """_event_row should expose duration and stat columns for an event."""
    from cloudscope.controllers.event_analysis_controller import _event_row

    analysis = EventAnalysis(channel=0, roi_id=1)
    created = analysis.add_event(1.0, 2.0, plot_data=_plot_data())
    row = _event_row(created)

    assert row["event_id"] == int(created.id)
    assert row["event_type"] == EventType.USER.value
    assert row["x0"] == 1.0 and row["x1"] == 2.0
    for key in (
        "duration",
        "event_mean",
        "event_min",
        "event_max",
        "pre_mean",
        "post_mean",
        "event_n",
        "pre_n",
        "post_n",
    ):
        assert key in row
