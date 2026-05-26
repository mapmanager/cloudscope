"""Tests for EventAnalysisView headless behavior."""

from __future__ import annotations

from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisPlotData
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
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
    AnalysisCompleted,
    AnalysisKind,
    RunAnalysisIntent,
)
from cloudscope.state import PrimarySelection
from cloudscope.views.event_analysis_view import (
    EventAnalysisView,
    _event_columns,
    _load_event_analysis_class,
)


def _view() -> EventAnalysisView:
    return EventAnalysisView(event_bus=EventBus(), initially_visible=False)


# ---- _event_columns ----


def test_event_columns_has_expected_field_set() -> None:
    """Column definitions should include the expected event/pre/post stat columns."""
    names = {col.field for col in _event_columns()}
    expected = {
        "id",
        "event_type",
        "x0",
        "x1",
        "duration",
        "event_mean",
        "pre_mean",
        "post_mean",
        "event_n",
        "pre_n",
        "post_n",
    }
    assert expected.issubset(names)


# ---- intent emission ----


def test_add_event_publishes_begin_add_intent() -> None:
    """_add_event should publish a BeginAddAcqImageEventIntent with current selection."""
    bus = EventBus()
    intents: list[BeginAddAcqImageEventIntent] = []
    bus.subscribe(BeginAddAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._add_event()

    assert len(intents) == 1
    assert intents[0].selection.file_id == "f"


def test_edit_event_publishes_begin_edit_intent() -> None:
    """_edit_event should publish a BeginEditAcqImageEventIntent."""
    bus = EventBus()
    intents: list[BeginEditAcqImageEventIntent] = []
    bus.subscribe(BeginEditAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._edit_event()

    assert len(intents) == 1


def test_delete_selected_publishes_delete_intent() -> None:
    """_delete_selected should publish a DeleteSelectedAcqImageEventIntent."""
    bus = EventBus()
    intents: list[DeleteSelectedAcqImageEventIntent] = []
    bus.subscribe(DeleteSelectedAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)

    view._delete_selected()

    assert len(intents) == 1


def test_cancel_publishes_cancel_intent() -> None:
    """_cancel should publish a CancelAddAcqImageEventIntent."""
    bus = EventBus()
    intents: list[CancelAddAcqImageEventIntent] = []
    bus.subscribe(CancelAddAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)

    view._cancel()

    assert len(intents) == 1


def test_set_events_visible_publishes_visibility_intent() -> None:
    """_set_events_visible should publish a SetAcqImageEventsVisibleIntent."""
    bus = EventBus()
    intents: list[SetAcqImageEventsVisibleIntent] = []
    bus.subscribe(SetAcqImageEventsVisibleIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)

    view._set_events_visible(False)
    view._set_events_visible(True)

    assert [i.visible for i in intents] == [False, True]


# ---- _select_next wrapping ----


def test_select_next_with_no_rows_clears_selection() -> None:
    """_select_next with no rows should publish SelectAcqImageEventIntent(None)."""
    bus = EventBus()
    intents: list[SelectAcqImageEventIntent] = []
    bus.subscribe(SelectAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)

    view._select_next()

    assert intents and intents[0].event_id is None


def test_select_next_starts_from_first_when_no_selection() -> None:
    """_select_next with rows but no current selection should pick the first id."""
    bus = EventBus()
    intents: list[SelectAcqImageEventIntent] = []
    bus.subscribe(SelectAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view._rows = [{"event_id": 3}, {"event_id": 5}, {"event_id": 7}]
    view._selected_event_id = None

    view._select_next()

    assert intents[-1].event_id == 3


def test_select_next_wraps_at_end_of_list() -> None:
    """_select_next at the last id should wrap back to the first."""
    bus = EventBus()
    intents: list[SelectAcqImageEventIntent] = []
    bus.subscribe(SelectAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view._rows = [{"event_id": 1}, {"event_id": 2}]
    view._selected_event_id = 2

    view._select_next()

    assert intents[-1].event_id == 1


def test_select_next_picks_next_id_when_selected() -> None:
    """_select_next mid-list should advance by one."""
    bus = EventBus()
    intents: list[SelectAcqImageEventIntent] = []
    bus.subscribe(SelectAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view._rows = [{"event_id": 10}, {"event_id": 20}, {"event_id": 30}]
    view._selected_event_id = 10

    view._select_next()

    assert intents[-1].event_id == 20


# ---- _on_events_changed selection filter ----


def test_on_events_changed_ignored_for_other_selection() -> None:
    """Events for other selections should not update internal rows."""
    view = _view()
    view.current_selection = PrimarySelection(file_id="me", channel=0, roi_id=1)
    view._rows = []

    view._on_events_changed(
        AcqImageEventsChanged(
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
            rows=[{"event_id": 1, "id": "1"}],
            selected_event_id=1,
            visible=True,
            edit_mode=EventEditMode.NONE,
        )
    )
    view._on_events_changed(
        AcqImageEventsChanged(
            selection=PrimarySelection(file_id="me", channel=1, roi_id=1),
            rows=[{"event_id": 2, "id": "2"}],
            selected_event_id=2,
            visible=True,
            edit_mode=EventEditMode.NONE,
        )
    )

    assert view._rows == []


def test_on_events_changed_updates_state_for_matching_selection() -> None:
    """Matching selection should update rows, selected id, visibility, and edit mode."""
    view = _view()
    view.current_selection = PrimarySelection(file_id="me", channel=0, roi_id=1)

    view._on_events_changed(
        AcqImageEventsChanged(
            selection=PrimarySelection(file_id="me", channel=0, roi_id=1),
            rows=[{"event_id": 4, "id": "4"}],
            selected_event_id=4,
            visible=False,
            edit_mode=EventEditMode.ADD,
        )
    )

    assert view._rows == [{"event_id": 4, "id": "4"}]
    assert view._selected_event_id == 4
    assert view._events_visible is False
    assert view._edit_mode is EventEditMode.ADD


# ---- _on_selection_changed updates id ----


def test_on_selection_changed_updates_selected_event_id() -> None:
    """Selection state events should update the internal selected event id."""
    view = _view()
    view._on_selection_changed(AcqImageEventSelectionChanged(selected_event_id=42))

    assert view._selected_event_id == 42

    view._on_selection_changed(AcqImageEventSelectionChanged(selected_event_id=None))
    assert view._selected_event_id is None


# ---- _on_row_selected guards ----


def test_on_row_selected_publishes_select_intent_when_idle() -> None:
    """_on_row_selected should publish SelectAcqImageEventIntent when not editing."""
    bus = EventBus()
    intents: list[SelectAcqImageEventIntent] = []
    bus.subscribe(SelectAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)

    view._on_row_selected({"event_id": 7, "id": "7"})

    assert intents and intents[-1].event_id == 7


def test_on_row_selected_suppressed_during_edit() -> None:
    """_on_row_selected should suppress intents while in edit mode."""
    bus = EventBus()
    intents: list[SelectAcqImageEventIntent] = []
    bus.subscribe(SelectAcqImageEventIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view._edit_mode = EventEditMode.EDIT

    view._on_row_selected({"event_id": 7, "id": "7"})

    assert intents == []


# ---- _on_analysis_completed filter ----


def test_on_analysis_completed_filters_other_kinds_and_selections() -> None:
    """_on_analysis_completed should only react to EVENT/RADON_VELOCITY for current selection."""
    view = _view()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    calls: list[str] = []
    view._build_results_controls = lambda: calls.append("build")  # type: ignore[method-assign]
    view._request_events_refresh = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.EVENT,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.EVENT,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )

    assert calls == ["build", "refresh"]


# ---- refresh_from_state delegates to request ----


def test_refresh_from_state_publishes_refresh_intent() -> None:
    """refresh_from_state should request current rows via an intent."""
    bus = EventBus()
    intents: list[RequestAcqImageEventsRefreshIntent] = []
    bus.subscribe(RequestAcqImageEventsRefreshIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view.refresh_from_state()

    assert len(intents) == 1
    assert intents[0].selection.file_id == "f"


# ---- _can_run_event_analysis ----


class _FakeAnalysis:
    def __init__(self, has_plot: bool) -> None:
        self._has_plot = has_plot

    def get_plot_data(self):
        if not self._has_plot:
            return None
        return AnalysisPlotData(
            x=(0.0, 1.0),
            y=(0.0, 1.0),
            x_label="t",
            y_label="v",
            series_name="radon",
        )


class _FakeSet:
    def __init__(self, items: dict[AnalysisKey, _FakeAnalysis]) -> None:
        self._items = items

    def get(self, key):
        return self._items.get(key)


class _FakeAcqImage:
    def __init__(self, analysis_set: _FakeSet) -> None:
        self.analysis_set = analysis_set


def test_can_run_event_analysis_false_without_acq_image() -> None:
    """Without a selected acq image, _can_run should be False."""
    view = _view()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view.get_selected_acq_image = lambda: None  # type: ignore[method-assign]

    assert view._can_run_event_analysis() is False


def test_can_run_event_analysis_false_without_radon_parent() -> None:
    """Without a Radon parent analysis, _can_run should be False."""
    view = _view()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view.get_selected_acq_image = lambda: _FakeAcqImage(_FakeSet({}))  # type: ignore[method-assign]

    assert view._can_run_event_analysis() is False


def test_can_run_event_analysis_false_without_plot_data() -> None:
    """Parent analysis without plot data should still report False."""
    view = _view()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    parent_key = AnalysisKey("radon_velocity", 0, 1)
    view.get_selected_acq_image = lambda: _FakeAcqImage(  # type: ignore[method-assign]
        _FakeSet({parent_key: _FakeAnalysis(has_plot=False)})
    )

    assert view._can_run_event_analysis() is False


def test_can_run_event_analysis_true_with_plot_data() -> None:
    """A parent with plot data should return True."""
    view = _view()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    parent_key = AnalysisKey("radon_velocity", 0, 1)
    view.get_selected_acq_image = lambda: _FakeAcqImage(  # type: ignore[method-assign]
        _FakeSet({parent_key: _FakeAnalysis(has_plot=True)})
    )

    assert view._can_run_event_analysis() is True


# ---- _run_event_analysis branches ----


def test_run_event_analysis_publishes_intent_for_complete_selection() -> None:
    """A complete selection should publish RunAnalysisIntent for EVENT kind."""
    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._run_event_analysis()

    assert len(intents) == 1
    assert intents[0].analysis_kind is AnalysisKind.EVENT


def test_run_event_analysis_noop_for_incomplete_selection(monkeypatch) -> None:
    """Incomplete selection should not publish an intent."""
    import cloudscope.views.event_analysis_view as mod

    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view.current_selection = PrimarySelection(file_id=None, channel=0, roi_id=1)

    monkeypatch.setattr(mod.ui, "notify", lambda *args, **kwargs: None)
    view._run_event_analysis()

    assert intents == []


# ---- _current_detection_params ----


def test_current_detection_params_uses_defaults_when_no_controls() -> None:
    """With no controls, defaults should be returned as-is."""
    cls = _load_event_analysis_class()
    assert cls is not None
    view = _view()

    params = view._current_detection_params()

    assert params == cls.get_default_detection_params()


# ---- on_primary_selection_changed resets state ----


def test_on_primary_selection_changed_resets_state_and_requests_refresh() -> None:
    """Primary selection changes should clear rows/selection/edit mode and refresh."""
    bus = EventBus()
    refresh_intents: list[RequestAcqImageEventsRefreshIntent] = []
    bus.subscribe(RequestAcqImageEventsRefreshIntent, refresh_intents.append)
    view = EventAnalysisView(event_bus=bus, initially_visible=False)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view._rows = [{"event_id": 1, "id": "1"}]
    view._selected_event_id = 1
    view._edit_mode = EventEditMode.ADD
    view._refresh_table = lambda: None  # type: ignore[method-assign]
    view._refresh_controls = lambda: None  # type: ignore[method-assign]
    view._sync_range_notification = lambda: None  # type: ignore[method-assign]
    view._build_results_controls = lambda: None  # type: ignore[method-assign]

    view.on_primary_selection_changed()

    assert view._rows == []
    assert view._selected_event_id is None
    assert view._edit_mode is EventEditMode.NONE
    assert refresh_intents
