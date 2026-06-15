"""Plotly figure generation for NicePool."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from nicewidgets.nicepool.dataframe_processor import DataFrameProcessor
from nicewidgets.nicepool.plot_state import PlotState, PlotType
from nicewidgets.nicepool.plot_summary import PlotSummary
from nicewidgets.nicepool.pre_filter_conventions import format_pre_filter_display


class FigureGenerator:
    """Generate Plotly figures from a DataFrame and PlotState.

    Args:
        data_processor: DataFrame processor.
        unique_row_id_col: Stable row identifier column.
    """

    def __init__(self, data_processor: DataFrameProcessor, *, unique_row_id_col: str) -> None:
        self.data_processor = data_processor
        self.unique_row_id_col = unique_row_id_col

    def make_figure(self, df_f: pd.DataFrame, state: PlotState) -> tuple[dict, PlotSummary]:
        """Build a Plotly figure dictionary and summary.

        Args:
            df_f: Pre-filtered DataFrame.
            state: Plot state.

        Returns:
            Tuple of figure dictionary and plot summary.
        """
        if state.plot_type == PlotType.HISTOGRAM:
            figure = self._histogram(df_f, state, cumulative=False)
        elif state.plot_type == PlotType.CUMULATIVE_HISTOGRAM:
            figure = self._histogram(df_f, state, cumulative=True)
        elif state.plot_type == PlotType.BOX_PLOT:
            figure = self._box_or_violin(df_f, state, violin=False)
        elif state.plot_type == PlotType.VIOLIN:
            figure = self._box_or_violin(df_f, state, violin=True)
        elif state.plot_type == PlotType.SWARM:
            figure = self._swarm(df_f, state)
        elif state.plot_type == PlotType.GROUPED:
            figure = self._grouped(df_f, state)
        else:
            figure = self._scatter(df_f, state)
        figure.update_layout(
            title=self._title(state),
            margin={"l": 50, "r": 20, "t": 55, "b": 50},
            showlegend=state.show_legend,
            dragmode="select",
        )
        return figure.to_dict(), PlotSummary(
            plot_type=state.plot_type.value,
            row_count=len(df_f),
            details={"x": state.xcol, "y": state.ycol, "filter": format_pre_filter_display(state.pre_filter)},
        )

    def _scatter(self, df_f: pd.DataFrame, state: PlotState) -> go.Figure:
        x = self.data_processor.get_x_values(
            df_f,
            state.xcol,
            use_absolute=state.use_absolute_value,
            use_remove_values=state.use_remove_values,
            remove_values_threshold=state.remove_values_threshold,
        )
        y = self.data_processor.get_y_values(
            df_f,
            state.ycol,
            use_absolute=state.use_absolute_value,
            use_remove_values=state.use_remove_values,
            remove_values_threshold=state.remove_values_threshold,
        )
        fig = go.Figure()
        group_col = state.group_col if state.group_col in df_f.columns else None
        if group_col:
            for group, sub in df_f.assign(_x=x, _y=y).groupby(group_col, sort=True):
                fig.add_trace(self._scatter_trace(sub, str(group), state))
        else:
            fig.add_trace(self._scatter_trace(df_f.assign(_x=x, _y=y), "rows", state))
        fig.update_xaxes(title_text=state.xcol)
        fig.update_yaxes(title_text=state.ycol)
        return fig

    def _scatter_trace(self, df: pd.DataFrame, name: str, state: PlotState) -> go.Scatter:
        customdata = df[self.unique_row_id_col].map(str).tolist() if self.unique_row_id_col in df.columns else None
        return go.Scatter(
            x=df["_x"],
            y=df["_y"],
            mode="markers" if state.show_raw else "none",
            name=name,
            customdata=customdata,
            marker={"size": state.point_size},
        )

    def _histogram(self, df_f: pd.DataFrame, state: PlotState, *, cumulative: bool) -> go.Figure:
        values = self.data_processor.get_y_values(
            df_f,
            state.ycol,
            use_absolute=state.use_absolute_value,
            use_remove_values=state.use_remove_values,
            remove_values_threshold=state.remove_values_threshold,
        )
        fig = go.Figure()
        fig.add_trace(
            go.Histogram(
                x=values,
                nbinsx=int(state.histogram_bins),
                cumulative={"enabled": cumulative},
                name=state.ycol,
            )
        )
        fig.update_xaxes(title_text=state.ycol)
        fig.update_yaxes(title_text="count")
        return fig

    def _box_or_violin(self, df_f: pd.DataFrame, state: PlotState, *, violin: bool) -> go.Figure:
        y = self.data_processor.get_y_values(
            df_f,
            state.ycol,
            use_absolute=state.use_absolute_value,
            use_remove_values=state.use_remove_values,
            remove_values_threshold=state.remove_values_threshold,
        )
        group_col = state.group_col if state.group_col in df_f.columns else None
        x = df_f[group_col].astype(str) if group_col else pd.Series(["rows"] * len(df_f), index=df_f.index)
        trace_cls = go.Violin if violin else go.Box
        fig = go.Figure()
        fig.add_trace(trace_cls(x=x, y=y, name=state.ycol, box_visible=True if violin else None, points="all"))
        fig.update_xaxes(title_text=group_col or "group")
        fig.update_yaxes(title_text=state.ycol)
        return fig

    def _swarm(self, df_f: pd.DataFrame, state: PlotState) -> go.Figure:
        group_col = state.group_col if state.group_col in df_f.columns else state.xcol
        groups = df_f[group_col].astype(str) if group_col in df_f.columns else pd.Series(["rows"] * len(df_f), index=df_f.index)
        categories = sorted(groups.dropna().unique())
        positions = {category: index for index, category in enumerate(categories)}
        y = self.data_processor.get_y_values(
            df_f,
            state.ycol,
            use_absolute=state.use_absolute_value,
            use_remove_values=state.use_remove_values,
            remove_values_threshold=state.remove_values_threshold,
        )
        rng = np.random.default_rng(seed=0)
        x = groups.map(positions).astype(float) + rng.uniform(-state.swarm_jitter_amount / 2, state.swarm_jitter_amount / 2, size=len(df_f))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker={"size": state.point_size}, name=state.ycol))
        fig.update_xaxes(title_text=group_col, tickvals=list(positions.values()), ticktext=list(positions.keys()))
        fig.update_yaxes(title_text=state.ycol)
        return fig

    def _grouped(self, df_f: pd.DataFrame, state: PlotState) -> go.Figure:
        group_col = state.group_col if state.group_col in df_f.columns else state.xcol
        y = self.data_processor.get_y_values(
            df_f,
            state.ycol,
            use_absolute=state.use_absolute_value,
            use_remove_values=state.use_remove_values,
            remove_values_threshold=state.remove_values_threshold,
        )
        tmp = pd.DataFrame({"group": df_f[group_col].astype(str), "y": y}).dropna()
        grouped = tmp.groupby("group", sort=True)["y"]
        if state.ystat == "median":
            values = grouped.median()
        elif state.ystat == "sum":
            values = grouped.sum()
        elif state.ystat == "count":
            values = grouped.count()
        elif state.ystat == "std":
            values = grouped.std()
        elif state.ystat == "sem":
            values = grouped.sem()
        elif state.ystat == "min":
            values = grouped.min()
        elif state.ystat == "max":
            values = grouped.max()
        elif state.ystat == "cv":
            mean = grouped.mean()
            std = grouped.std()
            values = std / mean.where(mean.abs() >= state.cv_epsilon)
        else:
            values = grouped.mean()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=values.index.tolist(), y=values.values.tolist(), name=state.ystat))
        fig.update_xaxes(title_text=group_col)
        fig.update_yaxes(title_text=f"{state.ystat}({state.ycol})")
        return fig

    def _title(self, state: PlotState) -> str:
        return f"{state.plot_type.value}: {state.ycol} ({format_pre_filter_display(state.pre_filter)})"
