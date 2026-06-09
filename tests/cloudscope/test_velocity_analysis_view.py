"""Tests for VelocityAnalysisView non-UI behavior."""

from __future__ import annotations

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind, RunAnalysisIntent
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.event_analysis_view import EventAnalysisView
from cloudscope.views.velocity_analysis_view import (
    _EMBEDDED_EVENT_TABLE_HEIGHT_PX,
    VelocityAnalysisView,
    _load_radon_velocity_analysis_class,
)
from cloudscope.views.view_ids import ViewId


# ---- identity / lifecycle ----


def test_velocity_analysis_view_is_base_view() -> None:
    """VelocityAnalysisView should participate in BaseView lifecycle."""
    view = VelocityAnalysisView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.VELOCITY_ANALYSIS


def test_velocity_analysis_view_owns_event_analysis_view(tmp_path) -> None:
    """VelocityAnalysisView should embed the event editor controls."""
    config = AppConfig.load(config_path=tmp_path / "app_config.json")
    view = VelocityAnalysisView(event_bus=EventBus(), app_config=config)

    assert isinstance(view.event_analysis_view, EventAnalysisView)
    assert view.event_analysis_view.is_visible is True


def test_velocity_analysis_view_embeds_event_view_with_fixed_table_height() -> None:
    """Embedded event view should use a fixed table height so it renders inline."""
    view = VelocityAnalysisView(event_bus=EventBus())

    assert view.event_analysis_view._table_height_px == _EMBEDDED_EVENT_TABLE_HEIGHT_PX


def test_velocity_analysis_view_forwards_subscription_lifecycle_to_event_view() -> None:
    """Embedded event view stays visible; only its subscriptions follow velocity."""
    view = VelocityAnalysisView(event_bus=EventBus(), initially_visible=False)
    event_view = view.event_analysis_view

    view.set_visible(True)
    assert event_view.is_visible is True
    assert len(event_view._subscriptions) > 0

    view.set_visible(False)
    assert event_view.is_visible is True
    assert len(event_view._subscriptions) == 0


def test_velocity_analysis_view_selection_snapshot_uses_base_selection() -> None:
    """Selection snapshot should copy the BaseView cached selection."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=1, roi_id=2)

    snapshot = view._selection_snapshot()

    assert snapshot == PrimarySelection(file_id='/tmp/a.oir', channel=1, roi_id=2)
    assert snapshot is not view.current_selection


def test_velocity_analysis_view_has_no_view_level_cancel_button() -> None:
    """Cancellation should be handled by TaskProgressDialogView, not this panel."""
    view = VelocityAnalysisView(event_bus=EventBus())

    assert not hasattr(view, '_cancel_button')


def test_velocity_analysis_view_refreshes_on_roi_changed_for_current_file() -> None:
    """VelocityAnalysisView should refresh when ROI model changes for current file."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    calls = []
    view._refresh_selection_dependent_ui = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=None),
        )
    )
    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=None),
        )
    )

    assert calls == ["refresh"]


# ---- _on_analysis_completed filter ----


def test_velocity_view_refreshes_results_only_for_matching_radon() -> None:
    """_on_analysis_completed should rebuild results only for RADON_VELOCITY of current selection."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    calls: list[str] = []
    view._build_results_controls = lambda: calls.append("build")  # type: ignore[method-assign]

    matching = AnalysisCompleted(
        analysis_kind=AnalysisKind.RADON_VELOCITY,
        selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
        success=True,
    )
    wrong_kind = AnalysisCompleted(
        analysis_kind=AnalysisKind.DIAMETER,
        selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
        success=True,
    )
    other_selection = AnalysisCompleted(
        analysis_kind=AnalysisKind.RADON_VELOCITY,
        selection=PrimarySelection(file_id="g", channel=0, roi_id=1),
        success=True,
    )

    view._on_analysis_completed(matching)
    view._on_analysis_completed(wrong_kind)
    view._on_analysis_completed(other_selection)

    assert calls == ["build"]


# ---- _current_detection_params from controls ----


class _FakeControl:
    def __init__(self, value: object) -> None:
        self.value = value
        self.visible = True


def test_current_detection_params_overrides_defaults_from_controls() -> None:
    """_current_detection_params should overlay control values onto defaults."""
    cls = _load_radon_velocity_analysis_class()
    assert cls is not None
    view = VelocityAnalysisView(event_bus=EventBus())
    defaults = cls.get_default_detection_params()
    new_window = next(c for c in cls.get_detection_schema() if c.name == "window_width").default
    view._param_controls = {"window_width": _FakeControl(int(new_window))}

    params = view._current_detection_params()

    assert params == {**defaults, "window_width": int(new_window)}


# ---- _on_run_clicked guards (publish path) ----


def test_on_run_clicked_emits_intent_for_complete_selection() -> None:
    """A complete selection should publish a RunAnalysisIntent for RADON_VELOCITY."""
    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = VelocityAnalysisView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    cls = _load_radon_velocity_analysis_class()
    assert cls is not None
    view._param_controls = {}

    view._on_run_clicked()

    assert len(intents) == 1
    assert intents[0].analysis_kind is AnalysisKind.RADON_VELOCITY
    assert intents[0].selection.file_id == "f"
    assert intents[0].detection_params == cls.get_default_detection_params()


def test_on_run_clicked_noop_for_incomplete_selection(monkeypatch) -> None:
    """Incomplete selection should not publish an intent (ui.notify replaced)."""
    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = VelocityAnalysisView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id="f", channel=None, roi_id=1)

    import cloudscope.views.velocity_analysis_view as mod

    monkeypatch.setattr(mod.ui, "notify", lambda *args, **kwargs: None)
    view._on_run_clicked()

    assert intents == []


# ---- _refresh_run_button + refresh_selection_label with fakes ----


class _FakeButton:
    def __init__(self) -> None:
        self.enabled = False
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


class _FakeLabel:
    def __init__(self) -> None:
        self.text = ""


def test_refresh_run_button_uses_valid_selection_helper() -> None:
    """_refresh_run_button should enable when has_valid_primary_selection() is True."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view._run_button = _FakeButton()
    view.has_valid_primary_selection = lambda: True  # type: ignore[method-assign]

    view._refresh_run_button()

    assert view._run_button.enabled is True


# ---- copy results to clipboard ----


class _FakeResult:
    def __init__(self, table: object) -> None:
        self.table = table


class _FakeAnalysis:
    def __init__(self, table: object, bookkeeping: object) -> None:
        self.result = _FakeResult(table)
        self._bookkeeping = bookkeeping

    def table_with_bookkeeping(self) -> object:
        return self._bookkeeping


def test_on_copy_results_copies_tsv(monkeypatch) -> None:
    """Copy handler should write the bookkeeping table as TSV to the clipboard."""
    import pandas as pd

    import cloudscope.views.velocity_analysis_view as mod

    captured: dict[str, str] = {}
    monkeypatch.setattr(mod, "copy_to_clipboard", lambda text: captured.update(text=text))
    monkeypatch.setattr(mod.ui, "notify", lambda *args, **kwargs: None)

    view = VelocityAnalysisView(event_bus=EventBus())
    bookkeeping = pd.DataFrame({"channel": [0], "roi_id": [1], "velocity": [1.5]})
    analysis = _FakeAnalysis(table=pd.DataFrame({"velocity": [1.5]}), bookkeeping=bookkeeping)
    view._selected_analysis = lambda: analysis  # type: ignore[method-assign]

    view._on_copy_results_clicked()

    assert "\t" in captured["text"]
    assert "velocity" in captured["text"]
    assert "channel" in captured["text"]


def test_on_copy_results_noop_when_no_table(monkeypatch) -> None:
    """Copy handler should not touch the clipboard when there is no result table."""
    import cloudscope.views.velocity_analysis_view as mod

    calls: list[str] = []
    monkeypatch.setattr(mod, "copy_to_clipboard", lambda text: calls.append(text))
    monkeypatch.setattr(mod.ui, "notify", lambda *args, **kwargs: None)

    view = VelocityAnalysisView(event_bus=EventBus())
    view._selected_analysis = lambda: None  # type: ignore[method-assign]

    view._on_copy_results_clicked()

    assert calls == []


def test_refresh_run_button_disables_copy_without_results() -> None:
    """Copy button should be disabled when the selection has no result table."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view._copy_button = _FakeButton()
    view._selected_analysis = lambda: None  # type: ignore[method-assign]

    view._refresh_run_button()

    assert view._copy_button.enabled is False


def test_refresh_selection_label_displays_no_file_when_unset() -> None:
    """No file selection should set the label to 'No file selected'."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view._selection_label = _FakeLabel()

    view.refresh_selection_label()

    assert view._selection_label.text == "No file selected"


def test_refresh_selection_label_includes_selection_components() -> None:
    """A complete selection should render file name, channel, and roi on 3 lines."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view._selection_label = _FakeLabel()
    view.current_selection = PrimarySelection(
        file_id="/abs/path/to/sample.oir", channel=2, roi_id=5
    )

    view.refresh_selection_label()

    lines = view._selection_label.text.split("\n")
    assert lines == ["file: sample.oir", "channel: 2", "roi: 5"]
