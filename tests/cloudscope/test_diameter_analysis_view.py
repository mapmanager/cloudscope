"""Tests for DiameterAnalysisView non-UI behavior."""

from __future__ import annotations

from acqstore.acq_image.analysis.model import DetectionParamSchema, DetectionValueType
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisCompleted,
    AnalysisKind,
    RunAnalysisIntent,
)
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.diameter_analysis_view import (
    DiameterAnalysisView,
    _field_visible_for_method,
    _load_diameter_analysis_class,
)
from cloudscope.views.view_ids import ViewId


# ---- _field_visible_for_method ----


def test_field_visible_for_method_true_when_no_methods_filter() -> None:
    """Fields without a ``methods`` filter should be visible for any selected method."""
    field = DetectionParamSchema(
        name="x",
        display_name="X",
        value_type=DetectionValueType.INT,
        default=0,
        description="",
    )
    assert _field_visible_for_method(field, "threshold_width") is True
    assert _field_visible_for_method(field, "other") is True


def test_field_visible_for_method_true_only_for_listed_methods() -> None:
    """Fields with a method filter should only be visible for listed methods."""
    field = DetectionParamSchema(
        name="x",
        display_name="X",
        value_type=DetectionValueType.INT,
        default=0,
        description="",
        methods=("threshold_width",),
    )
    assert _field_visible_for_method(field, "threshold_width") is True
    assert _field_visible_for_method(field, "other") is False


# ---- identity / lifecycle ----


def test_diameter_analysis_view_is_base_view() -> None:
    """DiameterAnalysisView should be a BaseView with the expected view id."""
    view = DiameterAnalysisView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.DIAMETER_ANALYSIS


def test_selection_snapshot_returns_independent_copy() -> None:
    """_selection_snapshot should return a copy of current_selection."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="f", channel=1, roi_id=2)

    snapshot = view._selection_snapshot()

    assert snapshot == PrimarySelection(file_id="f", channel=1, roi_id=2)
    assert snapshot is not view.current_selection


# ---- _on_analysis_completed filter ----


def test_on_analysis_completed_rebuilds_only_for_matching_diameter() -> None:
    """Only DIAMETER completions with matching selection should rebuild results."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    calls: list[str] = []
    view._build_results_controls = lambda: calls.append("build")  # type: ignore[method-assign]

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="g", channel=0, roi_id=1),
            success=True,
        )
    )

    assert calls == ["build"]


# ---- _on_roi_changed ----


def test_on_roi_changed_refreshes_only_when_file_matches() -> None:
    """ROI mutations for other files should not trigger a refresh."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    calls: list[str] = []
    view._refresh_selection_dependent_ui = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
        )
    )
    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
        )
    )

    assert calls == ["refresh"]


# ---- _selected_diameter_method ----


def test_selected_diameter_method_default_when_no_control() -> None:
    """Without a diameter_method control, default should be 'threshold_width'."""
    view = DiameterAnalysisView(event_bus=EventBus())
    assert view._selected_diameter_method() == "threshold_width"


class _FakeControl:
    def __init__(self, value: object) -> None:
        self.value = value
        self.visible = True
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


def test_selected_diameter_method_returns_control_value() -> None:
    """Selected method should reflect the diameter_method control value."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view._param_controls["diameter_method"] = _FakeControl("other_method")

    assert view._selected_diameter_method() == "other_method"


def test_selected_diameter_method_default_when_value_none() -> None:
    """None value should fall back to 'threshold_width'."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view._param_controls["diameter_method"] = _FakeControl(None)

    assert view._selected_diameter_method() == "threshold_width"


# ---- _refresh_param_visibility ----


def test_refresh_param_visibility_hides_fields_excluded_by_method() -> None:
    """Controls for fields whose methods filter excludes the selection should be hidden."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view._param_controls["diameter_method"] = _FakeControl("a")
    view._param_controls["only_a"] = _FakeControl(1.0)
    view._param_controls["only_b"] = _FakeControl(2.0)
    view._schema_by_name["only_a"] = DetectionParamSchema(
        name="only_a",
        display_name="A",
        value_type=DetectionValueType.FLOAT,
        default=1.0,
        description="",
        methods=("a",),
    )
    view._schema_by_name["only_b"] = DetectionParamSchema(
        name="only_b",
        display_name="B",
        value_type=DetectionValueType.FLOAT,
        default=2.0,
        description="",
        methods=("b",),
    )

    view._refresh_param_visibility()

    assert view._param_controls["only_a"].visible is True
    assert view._param_controls["only_b"].visible is False
    assert view._param_controls["only_a"].updates == 1
    assert view._param_controls["only_b"].updates == 1


# ---- _current_detection_params filters hidden controls ----


def test_current_detection_params_skips_hidden_controls() -> None:
    """Hidden controls should not contribute to the detection params dict."""
    cls = _load_diameter_analysis_class()
    assert cls is not None
    view = DiameterAnalysisView(event_bus=EventBus())
    defaults = cls.get_default_detection_params()

    visible_field_name = next(
        c.name for c in cls.get_detection_schema() if c.value_type.value in {"int", "float"} and c.visible
    )
    visible = _FakeControl(defaults[visible_field_name])
    hidden = _FakeControl(99999)
    hidden.visible = False
    view._param_controls[visible_field_name] = visible
    view._param_controls["some_other"] = hidden

    params = view._current_detection_params()

    assert params[visible_field_name] == defaults[visible_field_name]
    assert "some_other" not in params or params["some_other"] != 99999


# ---- _on_run_clicked publish + guard paths ----


def test_on_run_clicked_publishes_intent_for_complete_selection() -> None:
    """A complete selection should publish a RunAnalysisIntent for DIAMETER."""
    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = DiameterAnalysisView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._on_run_clicked()

    assert len(intents) == 1
    assert intents[0].analysis_kind is AnalysisKind.DIAMETER
    assert intents[0].selection.file_id == "f"


def test_on_run_clicked_noop_for_incomplete_selection(monkeypatch) -> None:
    """Incomplete selection should not publish an intent."""
    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = DiameterAnalysisView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id=None, channel=0, roi_id=1)

    import cloudscope.views.diameter_analysis_view as mod

    monkeypatch.setattr(mod.ui, "notify", lambda *args, **kwargs: None)
    view._on_run_clicked()

    assert intents == []


# ---- _refresh_run_button + refresh_selection_label ----


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
    """_refresh_run_button should toggle based on has_valid_primary_selection()."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view._run_button = _FakeButton()
    view.has_valid_primary_selection = lambda: True  # type: ignore[method-assign]

    view._refresh_run_button()

    assert view._run_button.enabled is True


def test_refresh_selection_label_no_file_set() -> None:
    """Without a file selected, the label should say 'No file selected'."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view._selection_label = _FakeLabel()

    view.refresh_selection_label()

    assert view._selection_label.text == "No file selected"


def test_refresh_selection_label_includes_selection_components() -> None:
    """A complete selection should render file name, channel, and roi on 3 lines."""
    view = DiameterAnalysisView(event_bus=EventBus())
    view._selection_label = _FakeLabel()
    view.current_selection = PrimarySelection(
        file_id="/abs/path/to/sample.oir", channel=1, roi_id=3
    )

    view.refresh_selection_label()

    lines = view._selection_label.text.split("\n")
    assert lines == ["file: sample.oir", "channel: 1", "roi: 3"]
