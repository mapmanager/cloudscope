"""Debug view for exercising client disconnect/reconnect and inspecting state."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.runtime import get_current_runtime
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId

# Browser-side Socket.IO helpers.  All disconnect/reconnect actions MUST run
# entirely in the browser (js_handler or ui.run_javascript) because once the
# socket is closed, Python-backed button callbacks cannot reach the server.
# See tmp/readme-disconnect-reconnect.md for the full rationale.
#
# NiceGUI 3.14.0 frontend sets ``window.socket`` in static/nicegui.js.

_DISCONNECT_SECONDS = 5

_DISCONNECT_AND_RECONNECT_JS = rf'''
() => {{
    console.log('[CloudScope debug] disconnecting for {_DISCONNECT_SECONDS}s');
    window.socket.disconnect();
    window.setTimeout(() => {{
        console.log('[CloudScope debug] reconnecting after {_DISCONNECT_SECONDS}s');
        window.socket.connect();
    }}, {_DISCONNECT_SECONDS * 1000});
}}
'''

_MANUAL_DISCONNECT_JS = r'''
() => {
    console.log('[CloudScope debug] manual disconnect');
    window.socket.disconnect();
}
'''

_MANUAL_RECONNECT_JS = r'''
() => {
    console.log('[CloudScope debug] manual reconnect');
    window.socket.connect();
}
'''


class DebugView(BaseView):
    """Developer panel for testing disconnect/reconnect and viewing app state.

    Disconnect/reconnect controls use browser-side ``js_handler`` callbacks so
    they work even when the Socket.IO connection is down.  A Python-backed
    reconnect button cannot work after disconnect because the click event
    cannot reach the server.

    Buttons and their exact actions (all run in the browser):

    * **Disconnect for N seconds** — runs ``window.socket.disconnect()``,
      then a browser ``setTimeout`` runs ``window.socket.connect()`` after N
      seconds.  Both operations are scheduled in the browser before the socket
      closes, so reconnect happens without any Python round-trip.  This is the
      deterministic single-click test.
    * **Disconnect** — runs ``window.socket.disconnect()`` and stays
      disconnected until Reconnect is clicked.
    * **Reconnect** — runs ``window.socket.connect()``.  May be unclickable
      while NiceGUI's connection-lost overlay is showing; in ``native=False``
      use the browser's JavaScript console instead.
    * **Refresh** (icon only) — Python callback that re-reads the stored app
      state into the read-out label.  Only works while connected.

    A read-only label shows the JSON of the currently stored, Python
    serializable app state.

    Args:
        event_bus: Page-scoped event bus.
        initially_visible: Whether the view starts visible.
    """

    view_id = ViewId.DEBUG
    disable_when_busy = False

    def __init__(self, *, event_bus: EventBus, initially_visible: bool = False) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._state_label: ui.label | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the debug card.

        Args:
            parent: Optional NiceGUI parent to build inside.

        Returns:
            Root element for this view.
        """
        root_classes = 'w-full h-full min-h-0 flex-1 overflow-y-auto pr-1'
        if parent is None:
            with ui.column().classes(root_classes) as self.root:
                self._build_card()
        else:
            with parent:
                with ui.column().classes(root_classes) as self.root:
                    self._build_card()
        self.after_build()
        return self.root

    def refresh_from_state(self) -> None:
        """Refresh the state read-out from the current runtime.

        Returns:
            None.
        """
        if self._state_label is None:
            return
        self._state_label.text = self._current_state_json()

    def _build_card(self) -> None:
        """Build the static debug card structure.

        Returns:
            None.
        """
        with ui.card().classes('w-full gap-3'):
            ui.label('Debug').classes('text-lg font-semibold')

            disconnect_reconnect_button = ui.button(
                f'Disconnect for {_DISCONNECT_SECONDS} seconds',
                icon='cloud_off',
            )
            disconnect_reconnect_button.on('click', js_handler=_DISCONNECT_AND_RECONNECT_JS)

            with ui.row().classes('w-full items-center gap-2'):
                disconnect_button = ui.button('Disconnect', icon='cloud_off')
                disconnect_button.on('click', js_handler=_MANUAL_DISCONNECT_JS)

                reconnect_button = ui.button('Reconnect', icon='cloud_done')
                reconnect_button.on('click', js_handler=_MANUAL_RECONNECT_JS)

                ui.button(icon='refresh', on_click=self.refresh_from_state).props(
                    'flat dense round'
                ).tooltip('Refresh state')

            ui.label('Stored app state').classes('text-sm font-semibold')
            self._state_label = ui.label(self._current_state_json()).classes(
                'w-full font-mono text-xs whitespace-pre-wrap break-all'
            )

    def _current_state_json(self) -> str:
        """Return the currently stored serializable app state as JSON text.

        Returns:
            Indented JSON string describing live selection and the last
            captured reconnect snapshot, or an error note if the runtime is
            unavailable.
        """
        try:
            state = self._collect_state()
        except Exception as exc:  # noqa: BLE001 - debug read-out must not raise
            return f'<unavailable: {exc!r}>'
        return json.dumps(state, indent=2, default=str)

    @staticmethod
    def _collect_state() -> dict[str, Any]:
        """Collect Python serializable state from the current runtime.

        Returns:
            Mapping describing where CloudScope keeps live per-session state:
            the live :class:`HomePageState` selection/x-range and the last
            captured reconnect snapshot on the runtime.
        """
        runtime = get_current_runtime()
        home_state = runtime.home_page_controller.state
        snapshot = runtime.session_snapshot
        return {
            'storage_location': 'CloudScopeRuntime (in-memory registry, not app.storage.*)',
            'live_home_page_state': home_state.to_debug_dict(),
            'session_snapshot': (
                None
                if snapshot is None
                else {
                    'chrome': dataclasses.asdict(snapshot.chrome),
                    'view_ids': sorted(snapshot.views.keys()),
                    'views': snapshot.views,
                }
            ),
        }
