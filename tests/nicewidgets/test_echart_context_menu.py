"""Tests for :class:`EChartWidget` display options, context menu, and default x-zoom cursor.

The widget's ``__init__`` requires NiceGUI's ``ui.echart`` / ``ui.context_menu``,
so most tests construct the widget via ``__new__`` and exercise pure-Python
helpers directly. The behavior we care about (display options, option dict
shape, context-menu builder labels, zoom-cursor payload) is isolated from the
NiceGUI runtime.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from nicewidgets.echart_widget.context_menu import EChartWidgetContextMenu
from nicewidgets.echart_widget.display_options import EChartDisplayOptions
from nicewidgets.echart_widget.models import EChartLineData
from nicewidgets.echart_widget.widget import EChartWidget, build_line_options


def _make_widget(
    *,
    display_options: EChartDisplayOptions | None = None,
    line_data: EChartLineData | None = None,
) -> EChartWidget:
    """Build an :class:`EChartWidget` without invoking ``__init__``."""
    w = EChartWidget.__new__(EChartWidget)
    w._line_data = line_data
    w._display_options = display_options or EChartDisplayOptions()
    return w


def test_display_options_default_hides_toolbar() -> None:
    """Default :class:`EChartDisplayOptions` ships with the toolbar hidden."""
    options = EChartDisplayOptions()
    assert options.show_toolbar is False


def test_display_options_default_hides_hover_info() -> None:
    """Default :class:`EChartDisplayOptions` ships with the hover tooltip hidden."""
    options = EChartDisplayOptions()
    assert options.show_hover_info is False


def test_empty_options_includes_toolbox_for_data_zoom_action() -> None:
    """The empty option dict must carry a ``toolbox.dataZoom`` feature.

    ECharts' ``dataZoomSelect`` cursor (used to enable click+drag x-axis zoom)
    requires the ``dataZoom`` feature to be present in the chart options,
    even when the toolbox icons themselves are hidden.
    """
    opts = EChartWidget._empty_options()
    assert "toolbox" in opts
    feature = opts["toolbox"]["feature"]
    assert "dataZoom" in feature


def test_apply_display_options_show_toolbar_propagates() -> None:
    """:meth:`_apply_display_options_to_options` flips ``toolbox.show``."""
    w_off = _make_widget(display_options=EChartDisplayOptions(show_toolbar=False))
    w_on = _make_widget(display_options=EChartDisplayOptions(show_toolbar=True))

    line = EChartLineData.from_sequences(
        x=[0.0, 1.0], y=[2.0, 3.0], x_label="x", y_label="y"
    )
    opts_off = build_line_options(line)
    opts_on = build_line_options(line)
    w_off._apply_display_options_to_options(opts_off)
    w_on._apply_display_options_to_options(opts_on)

    assert opts_off["toolbox"]["show"] is False
    assert opts_on["toolbox"]["show"] is True


def test_apply_display_options_show_hover_info_propagates() -> None:
    """:meth:`_apply_display_options_to_options` flips ``tooltip.show``.

    The ``trigger='axis'`` portion of the tooltip configuration is preserved
    so the axis pointer behavior remains stable across toggles.
    """
    w_off = _make_widget(display_options=EChartDisplayOptions(show_hover_info=False))
    w_on = _make_widget(display_options=EChartDisplayOptions(show_hover_info=True))

    line = EChartLineData.from_sequences(
        x=[0.0, 1.0], y=[2.0, 3.0], x_label="x", y_label="y"
    )
    opts_off = build_line_options(line)
    opts_on = build_line_options(line)
    w_off._apply_display_options_to_options(opts_off)
    w_on._apply_display_options_to_options(opts_on)

    assert opts_off["tooltip"]["show"] is False
    assert opts_off["tooltip"]["trigger"] == "axis"
    assert opts_on["tooltip"]["show"] is True
    assert opts_on["tooltip"]["trigger"] == "axis"


def test_apply_display_options_creates_missing_toolbox_and_tooltip() -> None:
    """Missing ``toolbox`` / ``tooltip`` keys are created so toggling does not raise."""
    w = _make_widget(
        display_options=EChartDisplayOptions(show_toolbar=True, show_hover_info=False)
    )
    options: dict[str, object] = {}
    w._apply_display_options_to_options(options)
    assert options["toolbox"]["show"] is True
    assert "feature" in options["toolbox"]
    assert options["tooltip"]["show"] is False
    assert options["tooltip"]["trigger"] == "axis"


def test_context_menu_labels_reflect_toggle_state() -> None:
    """Menu labels use a ``✓`` prefix only when the option is enabled."""
    on = EChartWidgetContextMenu._toggle_label("Show Toolbar", True)
    off = EChartWidgetContextMenu._toggle_label("Show Toolbar", False)
    assert on.startswith("✓ ")
    assert on.endswith("Show Toolbar")
    assert not off.startswith("✓ ")
    assert off == "Show Toolbar"


class _RecordingMenuItem:
    """Lightweight ``ui.menu_item`` replacement that records constructor args."""

    def __init__(self, label: str, *, on_click=None) -> None:
        self.label = label
        self.on_click = on_click


class _RecordingSeparator:
    """Lightweight ``ui.separator`` replacement."""


@pytest.fixture
def recording_ui(monkeypatch) -> Iterator[list[object]]:
    """Patch ``ui.menu_item`` and ``ui.separator`` to record build order."""
    recorded: list[object] = []

    def fake_menu_item(label, *, on_click=None):
        item = _RecordingMenuItem(label, on_click=on_click)
        recorded.append(item)
        return item

    def fake_separator():
        sep = _RecordingSeparator()
        recorded.append(sep)
        return sep

    monkeypatch.setattr(
        "nicewidgets.echart_widget.context_menu.ui.menu_item", fake_menu_item
    )
    monkeypatch.setattr(
        "nicewidgets.echart_widget.context_menu.ui.separator", fake_separator
    )
    yield recorded


def test_context_menu_builds_toggles_separator_and_clipboard_entries(
    recording_ui,
) -> None:
    """``build()`` produces toolbar/hover toggle items, a separator, and a Copy item."""
    widget = _make_widget(
        display_options=EChartDisplayOptions(show_toolbar=False, show_hover_info=True)
    )
    menu = EChartWidgetContextMenu(get_widget=lambda: widget)

    menu.build()

    assert len(recording_ui) == 4
    toolbar_item, hover_item, separator, copy_item = recording_ui
    assert isinstance(toolbar_item, _RecordingMenuItem)
    assert isinstance(hover_item, _RecordingMenuItem)
    assert isinstance(separator, _RecordingSeparator)
    assert isinstance(copy_item, _RecordingMenuItem)
    assert toolbar_item.label == "Show Toolbar"
    assert hover_item.label.endswith("Hover Info")
    assert hover_item.label.startswith("✓ ")
    assert copy_item.label == "Copy To Clipboard"


def test_context_menu_toolbar_item_flips_show_toolbar(recording_ui) -> None:
    """Clicking the toolbar menu item calls ``set_toolbar_visible`` with the inverse."""
    calls: list[bool] = []

    class _FakeWidget:
        display_options = EChartDisplayOptions(show_toolbar=False)

        def set_toolbar_visible(self, visible: bool) -> None:
            calls.append(bool(visible))

        def set_hover_info_visible(self, visible: bool) -> None:
            return None

        async def copy_plot_to_clipboard(self) -> None:
            return None

    fake = _FakeWidget()
    menu = EChartWidgetContextMenu(get_widget=lambda: fake)
    menu.build()

    toolbar_item = recording_ui[0]
    toolbar_item.on_click()
    assert calls == [True]


def test_context_menu_hover_item_flips_show_hover_info(recording_ui) -> None:
    """Clicking the hover-info menu item calls ``set_hover_info_visible`` with the inverse."""
    calls: list[bool] = []

    class _FakeWidget:
        display_options = EChartDisplayOptions(show_toolbar=False, show_hover_info=True)

        def set_toolbar_visible(self, visible: bool) -> None:
            return None

        def set_hover_info_visible(self, visible: bool) -> None:
            calls.append(bool(visible))

        async def copy_plot_to_clipboard(self) -> None:
            return None

    fake = _FakeWidget()
    menu = EChartWidgetContextMenu(get_widget=lambda: fake)
    menu.build()

    hover_item = recording_ui[1]
    hover_item.on_click()
    assert calls == [False]


def test_x_zoom_cursor_payload_is_data_zoom_select() -> None:
    """:meth:`_activate_x_zoom_cursor` dispatches the ``dataZoomSelect`` action."""
    calls: list[tuple[str, dict[str, object]]] = []

    class _FakeContainer:
        def run_chart_method(self, method: str, payload: dict[str, object]) -> None:
            calls.append((method, payload))

    w = _make_widget()
    w.container = _FakeContainer()  # type: ignore[assignment]
    w._activate_x_zoom_cursor()

    assert calls == [
        (
            "dispatchAction",
            {
                "type": "takeGlobalCursor",
                "key": "dataZoomSelect",
                "dataZoomSelectActive": True,
            },
        )
    ]


def test_cancel_select_x_range_reactivates_x_zoom_cursor() -> None:
    """Cancelling brush mode restores the default click+drag x-zoom cursor."""
    calls: list[tuple[str, dict[str, object]]] = []

    class _FakeContainer:
        def run_chart_method(self, method: str, payload: dict[str, object]) -> None:
            calls.append((method, payload))

    w = _make_widget()
    w._selecting_x = True
    w._pending_x_range = (1.0, 2.0)
    w.container = _FakeContainer()  # type: ignore[assignment]

    w.cancel_select_x_range()

    assert any(
        payload.get("key") == "dataZoomSelect"
        for method, payload in calls
        if method == "dispatchAction"
    )
    assert w._selecting_x is False
    assert w._pending_x_range is None
