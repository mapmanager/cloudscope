"""NiceGUI diagnostics page for CloudScope MVC telemetry."""

from __future__ import annotations

from datetime import datetime

from nicegui import ui

from cloudscope.devtools.mvc_telemetry import is_mvc_telemetry_enabled, mvc_telemetry


def register_mvc_diagnostics_page() -> None:
    """Register the development MVC telemetry page."""

    @ui.page('/dev/mvc')
    def mvc_diagnostics_page() -> None:
        ui.page_title('CloudScope MVC Telemetry')
        render_mvc_diagnostics_view()


def render_mvc_diagnostics_view() -> None:
    """Render the MVC telemetry diagnostics UI."""
    with ui.column().classes('w-full h-screen min-h-0 p-4 gap-3 overflow-hidden'):
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-0'):
                ui.label('CloudScope MVC Event Flow').classes('text-xl font-bold')
                enabled_text = 'enabled' if is_mvc_telemetry_enabled() else 'disabled'
                ui.label(f'Telemetry is {enabled_text}. Set CLOUDSCOPE_ENABLE_MVC_TELEMETRY=1 before launch.').classes(
                    'text-xs text-gray-500'
                )
            with ui.row().classes('gap-2'):
                ui.button('Clear', on_click=lambda: [mvc_telemetry.clear(), refresh()]).props('outline color=negative')
                ui.button('Refresh', on_click=lambda: refresh()).props('outline')

        summary_label = ui.label().classes('text-sm text-gray-600')
        chart = ui.echart(mvc_telemetry.build_echart_options()).classes('w-full h-[65vh] min-h-[420px] border rounded')

        with ui.expansion('Recent deliveries', value=True).classes('w-full'):
            recent_container = ui.column().classes('w-full max-h-56 overflow-auto gap-1')

        def refresh() -> None:
            summary = mvc_telemetry.summary()
            summary_label.text = (
                f"events: {summary['events']} | handlers: {summary['handlers']} | "
                f"edges: {summary['edges']} | deliveries: {summary['deliveries']} | errors: {summary['errors']}"
            )

            chart.options.clear()
            chart.options.update(mvc_telemetry.build_echart_options())
            chart.update()

            recent_container.clear()
            with recent_container:
                for record in mvc_telemetry.recent_records()[:30]:
                    timestamp = datetime.fromtimestamp(record.timestamp).strftime('%H:%M:%S')
                    sender = f'{record.sender_name} → ' if record.sender_name else ''
                    text = f'{timestamp}  {sender}{record.event_name} → {record.handler_name}  [{record.status}]'
                    if record.error:
                        text = f'{text}: {record.error}'
                    ui.label(text).classes('text-xs font-mono')

        refresh()
        ui.timer(2.0, refresh)
