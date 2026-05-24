from typing import Any
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import base64
import logging

import numpy as np
from nicegui import ui

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChartState(Enum):
    DEFAULT = 'default'
    USER_SELECT_X = 'user_select_x'


class PendingAction(Enum):
    NONE = 'none'
    ADD_RECT = 'add_rect'


class EventTypes(Enum):
    USER = 'user'
    RISE = 'rise'
    FALL = 'fall'
    TRANSIENT = 'transient'


@dataclass(slots=True)
class AcqImageEvent:
    id: int
    x0: float
    x1: float
    event_type: EventTypes = EventTypes.USER

    @property
    def duration(self) -> float:
        return abs(self.x1 - self.x0)


class AcqImageEventStore:
    """Pure backend/core store.

    No GUI state, no NiceGUI, no ECharts, no selected event, no style.
    """

    def __init__(self) -> None:
        self._events: dict[int, AcqImageEvent] = {}
        self._next_id = 1

    def add_rect(
        self,
        x0: float,
        x1: float,
        event_type: EventTypes = EventTypes.USER,
    ) -> AcqImageEvent:
        event_id = self._allocate_id()

        event = AcqImageEvent(
            id=event_id,
            x0=min(float(x0), float(x1)),
            x1=max(float(x0), float(x1)),
            event_type=event_type,
        )

        self._events[event.id] = event
        return event

    def add_rects(self, rects: list[AcqImageEvent]) -> list[AcqImageEvent]:
        added: list[AcqImageEvent] = []

        for rect in rects:
            event_id = int(rect.id)
            if event_id in self._events:
                raise ValueError(f'Event id already exists: {event_id}')

            event = AcqImageEvent(
                id=event_id,
                x0=min(float(rect.x0), float(rect.x1)),
                x1=max(float(rect.x0), float(rect.x1)),
                event_type=rect.event_type,
            )

            self._events[event.id] = event
            self._next_id = max(self._next_id, event.id + 1)
            added.append(event)

        return added

    def delete_rect(self, rect_id: int) -> None:
        rect_id = int(rect_id)

        if rect_id not in self._events:
            raise KeyError(f'No event with id: {rect_id}')

        del self._events[rect_id]

    def update_rect(
        self,
        rect_id: int,
        *,
        x0: float | None = None,
        x1: float | None = None,
        event_type: EventTypes | None = None,
    ) -> AcqImageEvent:
        rect_id = int(rect_id)

        if rect_id not in self._events:
            raise KeyError(f'No event with id: {rect_id}')

        old = self._events[rect_id]

        new_x0 = old.x0 if x0 is None else float(x0)
        new_x1 = old.x1 if x1 is None else float(x1)
        new_event_type = old.event_type if event_type is None else event_type

        updated = AcqImageEvent(
            id=old.id,
            x0=min(new_x0, new_x1),
            x1=max(new_x0, new_x1),
            event_type=new_event_type,
        )

        self._events[rect_id] = updated
        return updated

    def get_rects(self) -> list[AcqImageEvent]:
        return list(self._events.values())

    def _allocate_id(self) -> int:
        event_id = self._next_id
        self._next_id += 1
        return event_id


@dataclass(frozen=True, slots=True)
class EventStyle:
    fill_color: str
    line_color: str
    line_width: int = 2
    line_style: str = 'solid'  # solid | dashed | dotted


EVENT_STYLE_BY_TYPE: dict[EventTypes, EventStyle] = {
    EventTypes.USER: EventStyle(
        fill_color='rgba(64, 158, 255, 0.18)',
        line_color='#409eff',
        line_width=2,
        line_style='solid',
    ),
    EventTypes.RISE: EventStyle(
        fill_color='rgba(103, 194, 58, 0.18)',
        line_color='#67c23a',
        line_width=2,
        line_style='solid',
    ),
    EventTypes.FALL: EventStyle(
        fill_color='rgba(245, 108, 108, 0.18)',
        line_color='#f56c6c',
        line_width=2,
        line_style='solid',
    ),
    EventTypes.TRANSIENT: EventStyle(
        fill_color='rgba(230, 162, 60, 0.18)',
        line_color='#e6a23c',
        line_width=2,
        line_style='dashed',
    ),
}

SELECTED_EVENT_STYLE = EventStyle(
    fill_color='rgba(255, 214, 10, 0.32)',
    line_color='#ffd60a',
    line_width=4,
    line_style='solid',
)


class MyChart:
    def __init__(
        self,
        on_user_zoom_x: Callable[[float, float], None],
        on_user_brush_selected: Callable[[float, float], None],
    ):
        self.on_user_zoom_x = on_user_zoom_x
        self.on_user_brush_selected = on_user_brush_selected

        self.state = ChartState.DEFAULT
        self.pending_action = PendingAction.NONE

        self.event_store = AcqImageEventStore()
        self._selected_event_id: int | None = None

        self.x_domain_min: float | None = None
        self.x_domain_max: float | None = None
        self.is_dark = False

        self._pending_brush_x_range: tuple[float, float] | None = None

        self.options = self._get_echart_options()

        self.chart = ui.echart(self.options).classes('w-full h-96')

        self.chart.on('chart:datazoom', self._on_zoom)
        self.chart.on('chart:brushselected', self._on_brush_selected)
        self.chart.on('chart:mouseup', self._on_select_x_mouseup)
        self.chart.on('mouseup', self._on_select_x_mouseup)
        self.chart.on('chart:dblclick', self._on_double_click)
        self.chart.on('dblclick', self._on_double_click)

    # ---------------------------------------------------------------------
    # Event overlay public API
    # ---------------------------------------------------------------------

    def add_rect(
        self,
        x0: float,
        x1: float,
        event_type: EventTypes = EventTypes.USER,
    ) -> AcqImageEvent:
        event = self.event_store.add_rect(x0=x0, x1=x1, event_type=event_type)
        logger.info(
            f'add_rect: id={event.id}, x0={event.x0}, x1={event.x1}, '
            f'type={event.event_type.value}'
        )

        self.select_rect(event.id)
        return event

    def add_rects(self, rects: list[AcqImageEvent]) -> list[AcqImageEvent]:
        events = self.event_store.add_rects(rects)
        logger.info(f'add_rects: count={len(events)}')

        self._sync_events_to_mark_area()
        return events

    def delete_rect(self, rect_id: int) -> None:
        logger.info(f'delete_rect: id={rect_id}')

        self.event_store.delete_rect(rect_id)

        if self._selected_event_id == int(rect_id):
            self._selected_event_id = None

        self._sync_events_to_mark_area()

    def update_rect(
        self,
        rect_id: int,
        *,
        x0: float | None = None,
        x1: float | None = None,
        event_type: EventTypes | None = None,
    ) -> AcqImageEvent:
        event = self.event_store.update_rect(
            rect_id,
            x0=x0,
            x1=x1,
            event_type=event_type,
        )

        logger.info(
            f'update_rect: id={event.id}, x0={event.x0}, x1={event.x1}, '
            f'type={event.event_type.value}'
        )

        self._sync_events_to_mark_area()
        return event

    def select_rect(self, rect_id: int | None) -> None:
        logger.info(f'select_rect: id={rect_id}')

        if rect_id is not None:
            existing_ids = {event.id for event in self.event_store.get_rects()}
            if int(rect_id) not in existing_ids:
                raise KeyError(f'No event with id: {rect_id}')

            self._selected_event_id = int(rect_id)
        else:
            self._selected_event_id = None

        self._sync_events_to_mark_area()

    def select_next_rect(self) -> None:
        events = sorted(self.event_store.get_rects(), key=lambda event: event.id)
        if not events:
            logger.info('select_next_rect: no events')
            self.select_rect(None)
            return

        ids = [event.id for event in events]

        if self._selected_event_id not in ids:
            self.select_rect(ids[0])
            return

        current_index = ids.index(self._selected_event_id)
        next_index = (current_index + 1) % len(ids)
        self.select_rect(ids[next_index])

    def delete_selected_rect(self) -> None:
        if self._selected_event_id is None:
            logger.info('delete_selected_rect: no selected event')
            return

        self.delete_rect(self._selected_event_id)

    def begin_add_rect(self) -> None:
        logger.info('begin_add_rect')

        self.pending_action = PendingAction.ADD_RECT
        self.set_state(ChartState.USER_SELECT_X)

    def _sync_events_to_mark_area(self) -> None:
        self.options['series'][0]['markArea'] = self._events_to_mark_area()
        self._push_options()

    def _events_to_mark_area(self) -> dict[str, Any]:
        return {
            'silent': False,
            'label': {'show': False},
            'data': [
                self._event_to_mark_area_pair(event)
                for event in sorted(self.event_store.get_rects(), key=lambda item: item.id)
            ],
        }

    def _event_to_mark_area_pair(self, event: AcqImageEvent) -> list[dict[str, Any]]:
        style = self._style_for_event(event)

        return [
            {
                'name': str(event.id),
                'xAxis': event.x0,
                'itemStyle': {
                    'color': style.fill_color,
                    'borderColor': style.line_color,
                    'borderWidth': style.line_width,
                    'borderType': style.line_style,
                },
                'emphasis': {
                    'itemStyle': {
                        'color': style.fill_color,
                        'borderColor': style.line_color,
                        'borderWidth': style.line_width,
                        'borderType': style.line_style,
                    },
                },
                'label': {
                    'show': False,
                },
            },
            {
                'xAxis': event.x1,
            },
        ]

    def _style_for_event(self, event: AcqImageEvent) -> EventStyle:
        if event.id == self._selected_event_id:
            return SELECTED_EVENT_STYLE

        return EVENT_STYLE_BY_TYPE[event.event_type]

    # ---------------------------------------------------------------------
    # Chart state / user interaction
    # ---------------------------------------------------------------------

    def set_state(self, state: ChartState) -> None:
        logger.info(f'set_state: {self.state.value} -> {state.value}')

        self.state = state
        self._pending_brush_x_range = None

        self._clear_brush()

        if state == ChartState.DEFAULT:
            self._disable_brush_cursor()
            return

        if state == ChartState.USER_SELECT_X:
            self.chart.run_chart_method('dispatchAction', {
                'type': 'takeGlobalCursor',
                'key': 'brush',
                'brushOption': {
                    'brushType': 'lineX',
                    'brushMode': 'single',
                },
            })
            return

        raise ValueError(f'Unsupported chart state: {state}')

    def enter_user_select_x(self) -> None:
        self.pending_action = PendingAction.NONE
        self.set_state(ChartState.USER_SELECT_X)

    def cancel_user_select_x(self) -> None:
        self.pending_action = PendingAction.NONE
        self.set_state(ChartState.DEFAULT)

    async def export_png(self, path: Path) -> None:
        output_path = path.expanduser()
        logger.info(f'export_png: {output_path}')

        data_url = await self.chart.run_chart_method('getDataURL', {
            'type': 'png',
            'pixelRatio': 2,
            'backgroundColor': self.options.get('backgroundColor', '#ffffff'),
        })

        if not isinstance(data_url, str) or not data_url.startswith('data:image/png;base64,'):
            logger.error(f'export_png failed: unexpected data_url={data_url!r}')
            return

        png_base64 = data_url.split(',', 1)[1]
        png_bytes = base64.b64decode(png_base64)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(png_bytes)

        logger.info(f'export_png wrote: {output_path}')

    def reset_zoom_x(self) -> None:
        logger.info('reset_zoom_x')

        self.chart.run_chart_method('dispatchAction', {
            'type': 'dataZoom',
            'dataZoomId': 'dataZoomX',
            'start': 0,
            'end': 100,
        })

    def _on_double_click(self, e) -> None:
        logger.info('double-click: reset zoom')

        if self.state == ChartState.USER_SELECT_X:
            self.cancel_user_select_x()

        self.reset_zoom_x()

    def _on_brush_selected(self, e) -> None:
        if self.state != ChartState.USER_SELECT_X:
            return

        coord_range = self._extract_x_brush_range(e.args)
        if coord_range is None:
            return

        self._pending_brush_x_range = coord_range

    def _on_select_x_mouseup(self, e) -> None:
        if self.state != ChartState.USER_SELECT_X:
            return

        self._commit_user_select_x()

    def _commit_user_select_x(self) -> None:
        if self.state != ChartState.USER_SELECT_X:
            return

        if self._pending_brush_x_range is None:
            logger.info('USER_SELECT_X mouseup with no pending brush range')
            return

        x_min, x_max = self._pending_brush_x_range

        logger.info(f'commit USER_SELECT_X: x_min={x_min}, x_max={x_max}')

        pending_action = self.pending_action

        self.pending_action = PendingAction.NONE
        self.set_state(ChartState.DEFAULT)

        if pending_action == PendingAction.ADD_RECT:
            self.add_rect(x_min, x_max, event_type=EventTypes.USER)

        self.on_user_brush_selected(x_min, x_max)

    def _extract_x_brush_range(self, args: dict[str, Any]) -> tuple[float, float] | None:
        batch = args.get('batch', [])
        if not batch:
            return None

        areas = batch[0].get('areas', [])
        if not areas:
            return None

        area = areas[0]
        coord_range = area.get('coordRange')
        if coord_range is None or len(coord_range) != 2:
            return None

        x0 = float(coord_range[0])
        x1 = float(coord_range[1])

        return min(x0, x1), max(x0, x1)

    def _clear_brush(self) -> None:
        self.chart.run_chart_method('dispatchAction', {
            'type': 'brush',
            'command': 'clear',
            'areas': [],
        })

    def _disable_brush_cursor(self) -> None:
        self.chart.run_chart_method('dispatchAction', {
            'type': 'takeGlobalCursor',
            'key': 'brush',
            'brushOption': {
                'brushType': False,
            },
        })

    # ---------------------------------------------------------------------
    # Primary line plot API
    # ---------------------------------------------------------------------

    def set_zoom_x(self, x_min: float, x_max: float) -> None:
        logger.info(f'set_zoom_x: x_min={x_min}, x_max={x_max}')

        self.chart.run_chart_method('dispatchAction', {
            'type': 'dataZoom',
            'dataZoomId': 'dataZoomX',
            'startValue': x_min,
            'endValue': x_max,
        })

    def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
        logger.info(f'set_data: len={len(x)}')

        if len(x) == 0:
            self.x_domain_min = None
            self.x_domain_max = None
            self.options['series'][0]['data'] = []
            self._push_options()
            return

        self.x_domain_min = float(np.min(x))
        self.x_domain_max = float(np.max(x))

        self.options['xAxis']['min'] = self.x_domain_min
        self.options['xAxis']['max'] = self.x_domain_max

        self.options['series'][0]['data'] = [
            [float(x_val), float(y_val)]
            for x_val, y_val in zip(x, y, strict=True)
        ]

        self.options['dataZoom'][0]['start'] = 0
        self.options['dataZoom'][0]['end'] = 100
        self.options['dataZoom'][0].pop('startValue', None)
        self.options['dataZoom'][0].pop('endValue', None)

        self._push_options()

    def set_dark(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self._apply_theme()
        self._push_options()

    def _apply_theme(self) -> None:
        if self.is_dark:
            bg = '#121212'
            fg = '#eeeeee'
            grid = '#444444'
        else:
            bg = '#ffffff'
            fg = '#222222'
            grid = '#dddddd'

        self.options['backgroundColor'] = bg
        self.options['textStyle'] = {'color': fg}

        self.options['xAxis'].update({
            'axisLabel': {'color': fg},
            'axisLine': {'lineStyle': {'color': fg}},
            'splitLine': {'lineStyle': {'color': grid}},
        })

        self.options['yAxis'].update({
            'axisLabel': {'color': fg},
            'axisLine': {'lineStyle': {'color': fg}},
            'splitLine': {'lineStyle': {'color': grid}},
        })

        self.options['toolbox']['iconStyle'] = {'borderColor': fg}
        self.options['toolbox']['emphasis'] = {
            'iconStyle': {'borderColor': fg}
        }

    def _push_options(self) -> None:
        self.chart.options.clear()
        self.chart.options.update(self.options)
        self.chart.update()

    def _percent_to_x_value(
        self,
        start_percent: float,
        end_percent: float,
    ) -> tuple[float, float]:
        if self.x_domain_min is None or self.x_domain_max is None:
            raise RuntimeError('Cannot convert percent zoom before data domain is known.')

        span = self.x_domain_max - self.x_domain_min

        return (
            self.x_domain_min + (start_percent / 100.0) * span,
            self.x_domain_min + (end_percent / 100.0) * span,
        )

    def _on_zoom(self, e) -> None:
        batch = e.args.get('batch', [])
        if not batch:
            return

        item = batch[0]

        start_value = item.get('startValue')
        end_value = item.get('endValue')

        if start_value is None or end_value is None:
            start_percent = item.get('start')
            end_percent = item.get('end')

            if start_percent is None or end_percent is None:
                logger.warning('Zoom event had neither value nor percent range.')
                return

            start_value, end_value = self._percent_to_x_value(
                float(start_percent),
                float(end_percent),
            )

        self.on_user_zoom_x(float(start_value), float(end_value))

    def _get_echart_options(self) -> dict[str, Any]:
        return {
            'animation': False,
            'animationDuration': 0,
            'animationDurationUpdate': 0,

            'backgroundColor': '#ffffff',
            'textStyle': {'color': '#222222'},

            'xAxis': {
                'type': 'value',
            },
            'yAxis': {
                'type': 'value',
            },
            'series': [
                {
                    'type': 'line',
                    'data': [],
                    'showSymbol': False,
                    'animation': False,
                    'animationDuration': 0,
                    'animationDurationUpdate': 0,
                    'markArea': self._events_to_mark_area(),
                }
            ],

            'dataZoom': [
                {
                    'type': 'inside',
                    'id': 'dataZoomX',
                    'xAxisIndex': 0,
                    'filterMode': 'none',
                    'start': 0,
                    'end': 100,
                },
            ],

            'brush': {
                'toolbox': ['lineX', 'clear'],
                'xAxisIndex': 0,
                'brushMode': 'single',
            },

            'toolbox': {
                'feature': {
                    'dataZoom': {
                        'yAxisIndex': 'none',
                    },
                    'restore': {},
                    'brush': {
                        'type': ['lineX', 'clear'],
                    },
                }
            },
        }


class EventControlsCard:
    def __init__(
        self,
        *,
        on_add: Callable[[], None],
        on_select_next: Callable[[], None],
        on_delete: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        with ui.card().classes('w-full'):
            ui.label('Events').classes('text-lg font-bold')

            with ui.row().classes('w-full items-center gap-2'):
                ui.button('+', on_click=on_add).props('title="Add event"')
                ui.button('Select Next', on_click=on_select_next)
                ui.button('Delete', on_click=on_delete).props('color=negative')
                ui.button('Cancel', on_click=on_cancel)


def sin_noise() -> tuple[np.ndarray, np.ndarray]:
    pnts = 30000
    stop = 200
    x = np.linspace(0, stop, pnts)
    y = np.sin(x) + np.random.normal(0, 0.1, pnts)
    return x, y


class HomePage:
    def __init__(self):
        self.dark_mode = ui.dark_mode(False)
        self.is_dark = False

        self._my_chart = MyChart(
            on_user_zoom_x=self.on_user_zoom_x,
            on_user_brush_selected=self.on_user_brush_selected,
        )

        ui.button('Set Data', on_click=self.set_data).classes('w-full')
        ui.button('Set Range 0–10', on_click=self.set_range).classes('w-full')
        ui.button('Reset Zoom', on_click=self.reset_zoom).classes('w-full')
        ui.button('Toggle Light/Dark', on_click=self.toggle_theme).classes('w-full')
        ui.button('Select X Range', on_click=self.select_x_range).classes('w-full')
        ui.button('Cancel Select X', on_click=self.cancel_select_x).classes('w-full')
        ui.button('Export PNG', on_click=self.export_png).classes('w-full')

        EventControlsCard(
            on_add=self.add_event,
            on_select_next=self.select_next_event,
            on_delete=self.delete_selected_event,
            on_cancel=self.cancel_select_x,
        )

        self.set_data()
        self.add_demo_events()

    def set_data(self) -> None:
        x, y = sin_noise()
        self._my_chart.set_data(x, y)

    def set_range(self) -> None:
        self._my_chart.set_zoom_x(x_min=0, x_max=10)

    def reset_zoom(self) -> None:
        self._my_chart.reset_zoom_x()

    def toggle_theme(self) -> None:
        self.is_dark = not self.is_dark
        self.dark_mode.value = self.is_dark
        self._my_chart.set_dark(self.is_dark)

    def select_x_range(self) -> None:
        self._my_chart.enter_user_select_x()

    def cancel_select_x(self) -> None:
        self._my_chart.cancel_user_select_x()

    def add_event(self) -> None:
        self._my_chart.begin_add_rect()

    def select_next_event(self) -> None:
        self._my_chart.select_next_rect()

    def delete_selected_event(self) -> None:
        self._my_chart.delete_selected_rect()

    def add_demo_events(self) -> None:
        self._my_chart.add_rects([
            AcqImageEvent(id=1, x0=20, x1=30, event_type=EventTypes.RISE),
            AcqImageEvent(id=2, x0=60, x1=75, event_type=EventTypes.FALL),
            AcqImageEvent(id=3, x0=120, x1=140, event_type=EventTypes.TRANSIENT),
        ])

    async def export_png(self) -> None:
        path = Path('~/Desktop/echart-export.png')
        logger.info(f'HomePage.export_png path={path.expanduser()}')
        await self._my_chart.export_png(path)

    def on_user_zoom_x(self, start_value: float, end_value: float) -> None:
        print(f'on_user_zoom_x: start_value={start_value}, end_value={end_value}')

    def on_user_brush_selected(self, x_min: float, x_max: float) -> None:
        print(f'on_user_brush_selected: x_min={x_min}, x_max={x_max}')


@ui.page('/')
def home_page() -> None:
    HomePage()


ui.run(native=True, window_size=(1024, 1024))
