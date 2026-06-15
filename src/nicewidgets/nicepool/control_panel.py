"""Left control panel for the full NicePool GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
from nicegui import ui

from nicewidgets.nicepool.plot_helpers import categorical_candidates, numeric_columns
from nicewidgets.nicepool.plot_state import PlotState, PlotType
from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE


class NicePoolControlPanel:
    """Build and read the NicePool left-side control panel.

    Args:
        df: Source DataFrame.
        initial_state: Initial plot state.
        pre_filter_options: Mapping from filter column to select options.
        layout: Initial plot layout string.
        current_plot_index: Current editable plot index.
        on_any_change: Callback for any state-changing control.
        on_layout_change: Callback for layout changes.
        on_plot_radio_change: Callback for current plot radio changes.
        on_apply_current_to_others: Callback for applying current state to all plots.
        on_replot_current: Callback for replotting current plot.
        on_reset_to_default: Callback for resetting plot states.
        on_copy_stats: Callback for copying plot summary stats.
        on_clear_selection: Optional callback to clear selection.
        show_save_button: Whether to render save button.
        on_save_config: Optional save-config callback.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        initial_state: PlotState,
        pre_filter_options: dict[str, list[str]],
        layout: str,
        current_plot_index: int,
        on_any_change: Callable[[], None],
        on_layout_change: Callable[[str], None],
        on_plot_radio_change: Callable[[Any], None],
        on_apply_current_to_others: Callable[[], None],
        on_replot_current: Callable[[], None],
        on_reset_to_default: Callable[[], None],
        on_copy_stats: Callable[[], None],
        on_clear_selection: Callable[[], None] | None = None,
        show_save_button: bool = False,
        on_save_config: Callable[[], None] | None = None,
    ) -> None:
        self.df = df
        self._initial_state = initial_state
        self._pre_filter_options = pre_filter_options
        self._layout = layout
        self._current_plot_index = current_plot_index
        self._on_any_change = on_any_change
        self._on_layout_change = on_layout_change
        self._on_plot_radio_change = on_plot_radio_change
        self._on_apply_current_to_others = on_apply_current_to_others
        self._on_replot_current = on_replot_current
        self._on_reset_to_default = on_reset_to_default
        self._on_copy_stats = on_copy_stats
        self._on_clear_selection = on_clear_selection
        self._show_save_button = show_save_button
        self._on_save_config = on_save_config
        self._pre_filter_selects: dict[str, ui.select] = {}
        self._layout_select: ui.select | None = None
        self._plot_radio: ui.radio | None = None
        self._type_select: ui.select | None = None
        self._x_select: ui.select | None = None
        self._y_select: ui.select | None = None
        self._group_select: ui.select | None = None
        self._color_grouping_select: ui.select | None = None
        self._ystat_select: ui.select | None = None
        self._cv_epsilon_input: ui.number | None = None
        self._histogram_bins_input: ui.number | None = None
        self._abs_value_checkbox: ui.checkbox | None = None
        self._swarm_jitter_amount_input: ui.number | None = None
        self._swarm_group_offset_input: ui.number | None = None
        self._use_remove_values_checkbox: ui.checkbox | None = None
        self._remove_values_threshold_input: ui.number | None = None
        self._show_mean_checkbox: ui.checkbox | None = None
        self._show_std_sem_checkbox: ui.checkbox | None = None
        self._std_sem_select: ui.select | None = None
        self._mean_line_width_input: ui.number | None = None
        self._error_line_width_input: ui.number | None = None
        self._show_raw_checkbox: ui.checkbox | None = None
        self._point_size_input: ui.number | None = None
        self._show_legend_checkbox: ui.checkbox | None = None

    def build(self) -> None:
        """Build the control panel in the current NiceGUI slot.

        Returns:
            None.
        """
        num_cols = numeric_columns(self.df)
        all_cols = [str(column) for column in self.df.columns]
        x_options = all_cols or [""]
        y_options = num_cols or all_cols or [""]
        group_options = [PRE_FILTER_NONE] + categorical_candidates(self.df)
        with ui.column().classes("w-full h-full p-3 gap-3 overflow-y-auto"):
            with ui.row().classes("w-full gap-2 items-center"):
                self._layout_select = ui.select(
                    options={"1x1": "1x1", "1x2": "1x2", "2x1": "2x1", "2x2": "2x2"},
                    value=self._layout,
                    label="Layout",
                    on_change=lambda event: self._on_layout_change(str(event.value)),
                ).classes("flex-1").props("dense outlined")
                if self._on_clear_selection is not None:
                    ui.button("Clear", on_click=self._on_clear_selection).props("dense")
                if self._show_save_button and self._on_save_config is not None:
                    ui.button("Save", on_click=self._on_save_config).props("dense")
            with ui.row().classes("w-full gap-2 items-center"):
                ui.label("Edit plot").classes("text-sm font-semibold")
                self._plot_radio = ui.radio(
                    ["1", "2", "3", "4"],
                    value=str(self._current_plot_index + 1),
                    on_change=self._on_plot_radio_change,
                ).props("inline dense")
            with ui.row().classes("w-full gap-2"):
                ui.button("Apply to Other", on_click=self._on_apply_current_to_others).classes("flex-1").props("dense")
                ui.button("Replot", on_click=self._on_replot_current).classes("flex-1").props("dense")
            with ui.row().classes("w-full gap-2"):
                ui.button("Reset Plots", on_click=self._on_reset_to_default).classes("flex-1").props("dense")
                ui.button("Copy stats", on_click=self._on_copy_stats).classes("flex-1").props("dense")
            with ui.card().classes("w-full p-2 gap-2"):
                ui.label("Pre Filter").classes("text-sm font-semibold")
                for column, options in self._pre_filter_options.items():
                    value = str(self._initial_state.pre_filter.get(column, PRE_FILTER_NONE))
                    if value not in options:
                        value = PRE_FILTER_NONE
                    self._pre_filter_selects[column] = ui.select(
                        options=options,
                        value=value,
                        label=column,
                        on_change=lambda _event=None: self._on_any_change(),
                    ).classes("w-full").props("dense outlined")
                self._abs_value_checkbox = ui.checkbox(
                    "Absolute Value",
                    value=self._initial_state.use_absolute_value,
                    on_change=lambda _event=None: self._on_any_change(),
                )
                with ui.row().classes("w-full gap-2 items-center"):
                    self._use_remove_values_checkbox = ui.checkbox(
                        "Remove Values",
                        value=self._initial_state.use_remove_values,
                        on_change=lambda _event=None: self._on_any_change(),
                    )
                    self._remove_values_threshold_input = ui.number(
                        label="Remove +/-",
                        value=self._initial_state.remove_values_threshold,
                        min=0.0,
                        step=0.1,
                        on_change=lambda _event=None: self._on_any_change(),
                    ).classes("flex-1").props("dense outlined")
            self._type_select = ui.select(
                options={plot_type.value: plot_type.value.replace("_", " ").title() for plot_type in PlotType},
                value=self._initial_state.plot_type.value,
                label="Plot type",
                on_change=lambda _event=None: self._on_any_change(),
            ).classes("w-full").props("dense outlined")
            self._x_select = ui.select(
                options=x_options,
                value=self._initial_state.xcol if self._initial_state.xcol in x_options else x_options[0],
                label="X column",
                on_change=lambda _event=None: self._on_any_change(),
            ).classes("w-full").props("dense outlined")
            self._y_select = ui.select(
                options=y_options,
                value=self._initial_state.ycol if self._initial_state.ycol in y_options else y_options[0],
                label="Y column",
                on_change=lambda _event=None: self._on_any_change(),
            ).classes("w-full").props("dense outlined")
            self._group_select = ui.select(
                options=group_options,
                value=self._initial_state.group_col if self._initial_state.group_col in group_options else PRE_FILTER_NONE,
                label="Group/Color",
                on_change=lambda _event=None: self._on_any_change(),
            ).classes("w-full").props("dense outlined")
            self._color_grouping_select = ui.select(
                options=group_options,
                value=self._initial_state.color_grouping if self._initial_state.color_grouping in group_options else PRE_FILTER_NONE,
                label="Group/Nesting",
                on_change=lambda _event=None: self._on_any_change(),
            ).classes("w-full").props("dense outlined")
            self._ystat_select = ui.select(
                options=["mean", "median", "sum", "count", "std", "sem", "min", "max", "cv"],
                value=self._initial_state.ystat,
                label="Y stat (grouped)",
                on_change=lambda _event=None: self._on_any_change(),
            ).classes("w-full").props("dense outlined")
            with ui.row().classes("w-full gap-2"):
                self._cv_epsilon_input = ui.number(
                    label="CV ε",
                    value=self._initial_state.cv_epsilon,
                    min=0.0,
                    step=0.01,
                    on_change=lambda _event=None: self._on_any_change(),
                ).classes("flex-1").props("dense outlined")
                self._histogram_bins_input = ui.number(
                    label="Histogram bins",
                    value=self._initial_state.histogram_bins,
                    min=5,
                    max=500,
                    step=5,
                    on_change=lambda _event=None: self._on_any_change(),
                ).classes("flex-1").props("dense outlined")
            with ui.card().classes("w-full p-2 gap-2"):
                ui.label("Swarm / statistics").classes("text-sm font-semibold")
                with ui.row().classes("w-full gap-2"):
                    self._swarm_jitter_amount_input = ui.number(
                        label="Jitter",
                        value=self._initial_state.swarm_jitter_amount,
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        on_change=lambda _event=None: self._on_any_change(),
                    ).classes("flex-1").props("dense outlined")
                    self._swarm_group_offset_input = ui.number(
                        label="Group offset",
                        value=self._initial_state.swarm_group_offset,
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        on_change=lambda _event=None: self._on_any_change(),
                    ).classes("flex-1").props("dense outlined")
                self._show_mean_checkbox = ui.checkbox(
                    "Show mean",
                    value=self._initial_state.show_mean,
                    on_change=lambda _event=None: self._on_any_change(),
                )
                self._show_std_sem_checkbox = ui.checkbox(
                    "Show std/sem",
                    value=self._initial_state.show_std_sem,
                    on_change=lambda _event=None: self._on_any_change(),
                )
                self._std_sem_select = ui.select(
                    options=["std", "sem"],
                    value=self._initial_state.std_sem_type,
                    label="Error type",
                    on_change=lambda _event=None: self._on_any_change(),
                ).classes("w-full").props("dense outlined")
                with ui.row().classes("w-full gap-2"):
                    self._mean_line_width_input = ui.number(
                        label="Mean line",
                        value=self._initial_state.mean_line_width,
                        min=1,
                        max=10,
                        step=1,
                        on_change=lambda _event=None: self._on_any_change(),
                    ).classes("flex-1").props("dense outlined")
                    self._error_line_width_input = ui.number(
                        label="Error line",
                        value=self._initial_state.error_line_width,
                        min=1,
                        max=10,
                        step=1,
                        on_change=lambda _event=None: self._on_any_change(),
                    ).classes("flex-1").props("dense outlined")
            with ui.card().classes("w-full p-2 gap-2"):
                ui.label("Display").classes("text-sm font-semibold")
                self._show_raw_checkbox = ui.checkbox(
                    "Show raw",
                    value=self._initial_state.show_raw,
                    on_change=lambda _event=None: self._on_any_change(),
                )
                self._show_legend_checkbox = ui.checkbox(
                    "Show legend",
                    value=self._initial_state.show_legend,
                    on_change=lambda _event=None: self._on_any_change(),
                )
                self._point_size_input = ui.number(
                    label="Point size",
                    value=self._initial_state.point_size,
                    min=1,
                    max=30,
                    step=1,
                    on_change=lambda _event=None: self._on_any_change(),
                ).classes("w-full").props("dense outlined")

    def read_state(self) -> PlotState:
        """Read current UI control values into a PlotState.

        Returns:
            Plot state.
        """
        pre_filter = {column: select.value for column, select in self._pre_filter_selects.items()}
        group_value = self._group_select.value if self._group_select is not None else PRE_FILTER_NONE
        color_value = self._color_grouping_select.value if self._color_grouping_select is not None else PRE_FILTER_NONE
        return PlotState(
            pre_filter=pre_filter,
            xcol=str(self._x_select.value if self._x_select is not None else ""),
            ycol=str(self._y_select.value if self._y_select is not None else ""),
            plot_type=PlotType(str(self._type_select.value if self._type_select is not None else PlotType.SCATTER.value)),
            group_col=None if group_value == PRE_FILTER_NONE else str(group_value),
            color_grouping=None if color_value == PRE_FILTER_NONE else str(color_value),
            ystat=str(self._ystat_select.value if self._ystat_select is not None else "mean"),
            cv_epsilon=float(self._cv_epsilon_input.value if self._cv_epsilon_input is not None else 0.01),
            histogram_bins=int(self._histogram_bins_input.value if self._histogram_bins_input is not None else 50),
            use_absolute_value=bool(self._abs_value_checkbox.value if self._abs_value_checkbox is not None else False),
            swarm_jitter_amount=float(self._swarm_jitter_amount_input.value if self._swarm_jitter_amount_input is not None else 0.35),
            swarm_group_offset=float(self._swarm_group_offset_input.value if self._swarm_group_offset_input is not None else 0.3),
            use_remove_values=bool(self._use_remove_values_checkbox.value if self._use_remove_values_checkbox is not None else False),
            remove_values_threshold=self._remove_values_threshold_input.value if self._remove_values_threshold_input is not None else None,
            show_mean=bool(self._show_mean_checkbox.value if self._show_mean_checkbox is not None else False),
            show_std_sem=bool(self._show_std_sem_checkbox.value if self._show_std_sem_checkbox is not None else False),
            std_sem_type=str(self._std_sem_select.value if self._std_sem_select is not None else "std"),
            mean_line_width=int(self._mean_line_width_input.value if self._mean_line_width_input is not None else 2),
            error_line_width=int(self._error_line_width_input.value if self._error_line_width_input is not None else 2),
            show_raw=bool(self._show_raw_checkbox.value if self._show_raw_checkbox is not None else True),
            point_size=int(self._point_size_input.value if self._point_size_input is not None else 6),
            show_legend=bool(self._show_legend_checkbox.value if self._show_legend_checkbox is not None else True),
        )
