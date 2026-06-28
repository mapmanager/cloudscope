"""Tests for the producer + consumer x-range wiring in primary views.

These tests verify the small bridge methods on :class:`PrimaryImageView` and
:class:`AcqAnalysisPlotView`; the underlying widgets are exercised in
``test_plotly_viewer_x_range.py`` and ``test_echart_x_range.py``.
"""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent
from cloudscope.views.acq_analysis_plot_view import AcqAnalysisPlotView
from cloudscope.views.primary_image_view import PrimaryImageView


class _FakePlotlyViewer:
    def __init__(self) -> None:
        self.has_data = True
        self.set_x_calls: list[tuple[float, float]] = []
        self.reset_calls = 0

    async def set_x_axis_range(self, *, x_min: float, x_max: float) -> None:
        self.set_x_calls.append((x_min, x_max))

    def reset_x_axis_range(self) -> None:
        self.reset_calls += 1


class _FakeChart:
    def __init__(self) -> None:
        self.set_calls: list[tuple[float | None, float | None]] = []
        self.reset_calls = 0
        self._x_min: float | None = None
        self._x_max: float | None = None

    @property
    def x_range_limits(self) -> tuple[float | None, float | None]:
        return (self._x_min, self._x_max)

    def set_x_axis_limits(self, x_min, x_max) -> None:
        self._x_min = x_min
        self._x_max = x_max
        self.set_calls.append((x_min, x_max))

    def reset_x_axis_limits(self) -> None:
        self._x_min = None
        self._x_max = None
        self.reset_calls += 1


def test_primary_image_view_publishes_intent_on_viewer_x_range() -> None:
    """``_on_viewer_x_range_changed`` publishes :class:`SetPrimaryXRangeIntent`."""
    bus = EventBus()
    view = PrimaryImageView(bus)
    seen: list[SetPrimaryXRangeIntent] = []
    bus.subscribe(SetPrimaryXRangeIntent, seen.append)

    view._on_viewer_x_range_changed(1.0, 4.0)
    view._primary_x_range = (1.0, 4.0)
    view._on_viewer_x_range_changed(None, None)

    assert seen == [
        SetPrimaryXRangeIntent(x_min=1.0, x_max=4.0),
        SetPrimaryXRangeIntent(x_min=None, x_max=None),
    ]


def test_primary_image_view_consumer_applies_to_viewer_when_has_data() -> None:
    """A chart-originated ``PrimaryXRangeChanged`` schedules ``set_x_axis_range``."""
    import asyncio

    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakePlotlyViewer()
    view._viewer = fake  # type: ignore[assignment]

    async def _run() -> None:
        view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=2.0, x_max=8.0))
        for _ in range(5):
            await asyncio.sleep(0)

    asyncio.run(_run())
    assert fake.set_x_calls == [(2.0, 8.0)]
    assert fake.reset_calls == 0


def test_primary_image_view_skips_self_echo_after_viewer_originated_range() -> None:
    """Viewer-originated x-range should not round-trip ``set_x_axis_range``."""
    import asyncio

    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakePlotlyViewer()
    view._viewer = fake  # type: ignore[assignment]

    view._on_viewer_x_range_changed(2.0, 8.0)
    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=2.0, x_max=8.0))

    async def _drain() -> None:
        for _ in range(5):
            await asyncio.sleep(0)

    asyncio.run(_drain())
    assert fake.set_x_calls == []
    assert view._primary_x_range == (2.0, 8.0)


def test_primary_image_view_consumer_auto_range_is_a_noop_for_viewer() -> None:
    """``(None, None)`` does NOT call the viewer reset.

    ``set_data`` auto-ranges the Plotly view on the new ``uirevision``; the
    consumer only overrides when state asks for a non-auto window.
    """
    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakePlotlyViewer()
    view._viewer = fake  # type: ignore[assignment]

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=None, x_max=None))
    assert fake.set_x_calls == []
    assert fake.reset_calls == 0
    assert view._primary_x_range == (None, None)


def test_primary_image_view_consumer_no_data_is_noop() -> None:
    """Without loaded data, the consumer skips the viewer update."""
    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakePlotlyViewer()
    fake.has_data = False
    view._viewer = fake  # type: ignore[assignment]

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=2.0, x_max=8.0))
    assert fake.set_x_calls == []
    assert fake.reset_calls == 0


def test_primary_image_view_caches_x_range_from_state_event() -> None:
    """The view caches the latest ``PrimaryXRangeChanged`` payload locally."""
    import asyncio

    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakePlotlyViewer()
    view._viewer = fake  # type: ignore[assignment]

    async def _run() -> None:
        view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=3.0, x_max=7.0))
        for _ in range(5):
            await asyncio.sleep(0)
        assert view._primary_x_range == (3.0, 7.0)

        view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=None, x_max=None))
        assert view._primary_x_range == (None, None)

    asyncio.run(_run())


def test_primary_image_view_apply_helper_skips_when_cache_is_auto() -> None:
    """``_apply_primary_x_range_to_viewer`` is a no-op when cache is ``(None, None)``."""
    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakePlotlyViewer()
    view._viewer = fake  # type: ignore[assignment]
    view._primary_x_range = (None, None)

    view._apply_primary_x_range_to_viewer()
    assert fake.set_x_calls == []
    assert fake.reset_calls == 0


def test_primary_image_view_apply_helper_re_applies_finite_cache() -> None:
    """``_apply_primary_x_range_to_viewer`` re-pushes a finite cached range.

    This is the behavior that survives a ``set_data`` rotation (e.g. analysis
    row click within the same file).
    """
    import asyncio

    bus = EventBus()
    view = PrimaryImageView(bus)
    fake = _FakePlotlyViewer()
    view._viewer = fake  # type: ignore[assignment]
    view._primary_x_range = (2.5, 6.5)

    async def _run() -> None:
        view._apply_primary_x_range_to_viewer()
        for _ in range(5):
            await asyncio.sleep(0)

    asyncio.run(_run())
    assert fake.set_x_calls == [(2.5, 6.5)]
    assert fake.reset_calls == 0


def test_acq_analysis_plot_view_publishes_intent_on_chart_x_range() -> None:
    """``_on_chart_x_range_changed`` publishes :class:`SetPrimaryXRangeIntent`."""
    bus = EventBus()
    view = AcqAnalysisPlotView(bus)
    seen: list[SetPrimaryXRangeIntent] = []
    bus.subscribe(SetPrimaryXRangeIntent, seen.append)

    view._on_chart_x_range_changed(0.5, 9.5)
    view._primary_x_range = (0.5, 9.5)
    view._on_chart_x_range_changed(None, None)

    assert seen == [
        SetPrimaryXRangeIntent(x_min=0.5, x_max=9.5),
        SetPrimaryXRangeIntent(x_min=None, x_max=None),
    ]


def test_acq_analysis_plot_view_skips_self_echo_after_chart_originated_range() -> None:
    """Chart-originated x-range should not round-trip ``set_x_axis_limits``."""
    bus = EventBus()
    view = AcqAnalysisPlotView(bus)
    fake = _FakeChart()
    view._chart = fake  # type: ignore[assignment]

    view._on_chart_x_range_changed(2.0, 8.0)
    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=2.0, x_max=8.0))

    assert fake.set_calls == []
    assert fake.reset_calls == 0
    assert view._primary_x_range == (2.0, 8.0)


def test_acq_analysis_plot_view_does_not_republish_when_cache_matches() -> None:
    """Duplicate chart datazoom after state sync must not publish another intent."""
    bus = EventBus()
    view = AcqAnalysisPlotView(bus)
    seen: list[SetPrimaryXRangeIntent] = []
    bus.subscribe(SetPrimaryXRangeIntent, seen.append)
    view._primary_x_range = (2.0, 8.0)

    view._on_chart_x_range_changed(2.0, 8.0)

    assert seen == []


def test_acq_analysis_plot_view_consumer_applies_to_chart() -> None:
    """Finite range -> ``set_x_axis_limits``; auto -> ``reset_x_axis_limits``."""
    bus = EventBus()
    view = AcqAnalysisPlotView(bus)
    fake = _FakeChart()
    view._chart = fake  # type: ignore[assignment]

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=1.0, x_max=2.0))
    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=None, x_max=None))

    assert fake.set_calls == [(1.0, 2.0)]
    assert fake.reset_calls == 1


def test_acq_analysis_plot_view_consumer_without_chart_is_noop() -> None:
    """No chart yet -> consumer skips silently."""
    bus = EventBus()
    view = AcqAnalysisPlotView(bus)
    view._chart = None  # type: ignore[assignment]

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=1.0, x_max=2.0))


def test_acq_analysis_plot_view_caches_x_range_from_state_event() -> None:
    """The view caches the latest ``PrimaryXRangeChanged`` payload locally."""
    bus = EventBus()
    view = AcqAnalysisPlotView(bus)
    fake = _FakeChart()
    view._chart = fake  # type: ignore[assignment]

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=3.0, x_max=7.0))
    assert view._primary_x_range == (3.0, 7.0)

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=None, x_max=None))
    assert view._primary_x_range == (None, None)


def test_acq_analysis_plot_view_apply_helper_reset_then_finite() -> None:
    """``_apply_primary_x_range_to_chart`` honors the cache idempotently."""
    bus = EventBus()
    view = AcqAnalysisPlotView(bus)
    fake = _FakeChart()
    view._chart = fake  # type: ignore[assignment]

    view._primary_x_range = (None, None)
    view._apply_primary_x_range_to_chart()
    assert fake.reset_calls == 0
    assert fake.set_calls == []

    fake._x_min = 0.0
    fake._x_max = 10.0
    view._primary_x_range = (1.0, 9.0)
    view._apply_primary_x_range_to_chart()
    assert fake.set_calls == [(1.0, 9.0)]
