"""Tests for SumIntensityAnalysisView."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acqstore.acq_image.analysis.model import (
    DetectionParamCategory,
    DetectionParamSchema,
    DetectionValueType,
)
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_analysis import (
    SumIntensityAnalysis,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind, RunAnalysisIntent
from cloudscope.events.roi import RoiChangeKind, RoiChanged
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.sum_intensity_analysis_view import (
    SumIntensityAnalysisView,
    _category_heading_if_changed,
    _field_visible_for_current_params,
)
from cloudscope.views.view_ids import ViewId


@dataclass
class _FakeControl:
    """Small stand-in for NiceGUI controls used by private view helpers."""

    value: object
    visible: bool = True
    updates: int = 0

    def update(self) -> None:
        """Record update calls."""
        self.updates += 1


def test_sum_intensity_analysis_view_identity() -> None:
    """SumIntensityAnalysisView should be a BaseView with expected view id."""
    view = SumIntensityAnalysisView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.SUM_INTENSITY_ANALYSIS


def test_category_heading_if_changed_returns_label_for_new_visible_category() -> None:
    """A visible field in a new category should emit that category label."""
    field = DetectionParamSchema(
        name="detrend_method",
        display_name="Detrend Method",
        value_type=DetectionValueType.ENUM,
        default="none",
        category=DetectionParamCategory.PREPROCESSING,
    )

    assert _category_heading_if_changed(None, field) == DetectionParamCategory.PREPROCESSING.value


def test_category_heading_if_changed_returns_none_for_same_category() -> None:
    """Repeated visible fields in one category should not emit another heading."""
    field = DetectionParamSchema(
        name="filter_method",
        display_name="Filter Method",
        value_type=DetectionValueType.ENUM,
        default="none",
        category=DetectionParamCategory.PREPROCESSING,
    )

    assert (
        _category_heading_if_changed(DetectionParamCategory.PREPROCESSING, field) is None
    )


def test_category_heading_if_changed_skips_schema_hidden_fields() -> None:
    """Schema-hidden fields should not emit category headings."""
    field = DetectionParamSchema(
        name="baseline_min_value",
        display_name="F0 Minimum Value",
        value_type=DetectionValueType.FLOAT,
        default=1e-12,
        visible=False,
        category=DetectionParamCategory.PREPROCESSING,
    )

    assert _category_heading_if_changed(None, field) is None


def test_category_headings_follow_visible_sum_intensity_schema() -> None:
    """Visible schema fields should produce one heading per category block."""
    current_category: DetectionParamCategory | None = None
    headings: list[str] = []
    for field in SumIntensityAnalysis.get_detection_schema():
        if not field.visible:
            continue
        heading = _category_heading_if_changed(current_category, field)
        if heading is not None:
            headings.append(heading)
            current_category = field.category

    assert headings == [
        DetectionParamCategory.PREPROCESSING.value,
        DetectionParamCategory.PEAK_DETECTION.value,
    ]


def test_sum_intensity_schema_hidden_fields_are_excluded_from_default_editor() -> None:
    """Default editor field set should come from schema ``visible`` metadata only."""
    visible_names = {
        field.name for field in SumIntensityAnalysis.get_detection_schema() if field.visible
    }

    assert "baseline_min_value" not in visible_names
    assert "level_fractions" not in visible_names
    assert "detrend_method" in visible_names
    assert "detection_method" in visible_names


def test_field_visible_for_current_params_without_methods() -> None:
    """Fields without method filters should always be visible."""
    field = DetectionParamSchema(
        name="x",
        display_name="X",
        value_type=DetectionValueType.FLOAT,
        default=0.0,
    )

    assert _field_visible_for_current_params(field, {}) is True


def test_field_visible_for_current_params_matches_any_active_control_value() -> None:
    """Method filters should match any active enum-like parameter value."""
    field = DetectionParamSchema(
        name="threshold",
        display_name="Threshold",
        value_type=DetectionValueType.FLOAT,
        default=1.0,
        methods=("derivative_threshold",),
    )

    assert _field_visible_for_current_params(field, {"detection_method": "derivative_threshold"}) is True
    assert _field_visible_for_current_params(field, {"detection_method": "absolute_threshold"}) is False


def test_selection_snapshot_returns_independent_copy() -> None:
    """_selection_snapshot should return a copied primary selection."""
    view = SumIntensityAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="f", channel=1, roi_id=2)

    snapshot = view._selection_snapshot()

    assert snapshot == PrimarySelection(file_id="f", channel=1, roi_id=2)
    assert snapshot is not view.current_selection


def test_on_analysis_completed_rebuilds_only_for_matching_sum_intensity() -> None:
    """Only matching SUM_INTENSITY completions should rebuild results."""
    view = SumIntensityAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    calls: list[str] = []
    view._build_results_controls = lambda: calls.append("build")  # type: ignore[method-assign]

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            selection=PrimarySelection(file_id="g", channel=0, roi_id=1),
            success=True,
        )
    )

    assert calls == ["build"]


def test_on_roi_changed_refreshes_only_when_file_matches() -> None:
    """ROI mutations for other files should not refresh the panel."""
    view = SumIntensityAnalysisView(event_bus=EventBus())
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


def test_refresh_param_visibility_uses_schema_method_filters() -> None:
    """Visibility should update using active control values and schema methods."""
    view = SumIntensityAnalysisView(event_bus=EventBus())
    view._param_controls["detection_method"] = _FakeControl("derivative_threshold")
    view._param_controls["derivative_threshold_per_sec"] = _FakeControl(1.0)
    view._param_controls["absolute_threshold"] = _FakeControl(0.1)
    view._schema_by_name["detection_method"] = DetectionParamSchema(
        name="detection_method",
        display_name="Detection Method",
        value_type=DetectionValueType.ENUM,
        default="derivative_threshold",
    )
    view._schema_by_name["derivative_threshold_per_sec"] = DetectionParamSchema(
        name="derivative_threshold_per_sec",
        display_name="Derivative Threshold",
        value_type=DetectionValueType.FLOAT,
        default=1.0,
        methods=("derivative_threshold",),
    )
    view._schema_by_name["absolute_threshold"] = DetectionParamSchema(
        name="absolute_threshold",
        display_name="Absolute Threshold",
        value_type=DetectionValueType.FLOAT,
        default=0.0,
        methods=("absolute_threshold",),
    )

    view._refresh_param_visibility()

    assert view._param_controls["derivative_threshold_per_sec"].visible is True
    assert view._param_controls["absolute_threshold"].visible is False


def test_current_detection_params_starts_from_selected_preset_and_visible_controls() -> None:
    """Current params should use preset values and overlay visible controls."""
    view = SumIntensityAnalysisView(event_bus=EventBus())
    view._preset_control = _FakeControl("fast")  # type: ignore[assignment]
    view._param_controls["derivative_threshold_per_sec"] = _FakeControl(12.5)
    hidden = _FakeControl(99.0, visible=False)
    view._param_controls["absolute_threshold"] = hidden

    params = view._current_detection_params()

    assert params["derivative_threshold_per_sec"] == 12.5
    assert params["baseline_method"] == "percentile"
    assert params["absolute_threshold"] != 99.0


def test_on_run_clicked_publishes_sum_intensity_intent_for_complete_selection() -> None:
    """A complete selection should publish a SUM_INTENSITY RunAnalysisIntent."""
    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = SumIntensityAnalysisView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view._preset_control = _FakeControl("medium")  # type: ignore[assignment]

    view._on_run_clicked()

    assert len(intents) == 1
    assert intents[0].analysis_kind is AnalysisKind.SUM_INTENSITY
    assert intents[0].selection == PrimarySelection(file_id="f", channel=0, roi_id=1)


def test_on_run_clicked_noop_for_incomplete_selection(monkeypatch) -> None:
    """Incomplete selection should not publish a run intent."""
    bus = EventBus()
    intents: list[RunAnalysisIntent] = []
    bus.subscribe(RunAnalysisIntent, intents.append)
    view = SumIntensityAnalysisView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id=None, channel=0, roi_id=1)

    import cloudscope.views.sum_intensity_analysis_view as mod

    monkeypatch.setattr(mod.ui, "notify", lambda *args, **kwargs: None)
    view._on_run_clicked()

    assert intents == []
