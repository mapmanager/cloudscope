"""Option C NiceGUI demo: one server, two windows or two browser tabs.

This demo is a reference architecture for a future CloudScope main window plus
standalone pool window.

It intentionally does NOT use:

    ui.run(native=True)

That NiceGUI-native shortcut was tested with NiceGUI 3.10.0 and failed for this
use case: calling ``webview.create_window(...)`` from a NiceGUI button handler
returned a pywebview Window object, but the second native window did not start
or display correctly.

Instead, this demo uses Option C:

    1. Run one NiceGUI server.
    2. Create pywebview windows manually in desktop mode.
    3. Point each window at a NiceGUI route.
    4. Use the same routes as normal browser tabs in web mode.

Desktop mode:
    Run one NiceGUI server with ``native=False`` and ``show=False``.
    Manually create a pywebview main window for ``/``.
    Open a pywebview pool window for ``/pool``.
    Both windows share one in-memory Python AppStore.

Web mode:
    Run one normal NiceGUI web server.
    Open ``/pool`` in a second browser tab.
    Both tabs share one in-memory Python AppStore in this demo.

Run desktop mode:
    CLOUDSCOPE_DEMO_MODE=desktop uv run python scripts/cloudscope/two_page_app/gpt_solution/multi_window_demo.py

Run web mode:
    CLOUDSCOPE_DEMO_MODE=web uv run python scripts/cloudscope/two_page_app/gpt_solution/multi_window_demo.py

Docker/web mode uses the same environment variables:
    CLOUDSCOPE_DEMO_MODE=web
    CLOUDSCOPE_HOST=0.0.0.0
    PORT=8080

This demo proves:

    1. Main and pool are separate UI surfaces.
    2. Main can open pool.
    3. Main and pool can update shared selection.
    4. Main and pool can mutate shared row data.
    5. Both views refresh from the same server-side store.
    6. Desktop mode can use true pywebview OS windows without multiprocessing.
    7. Web mode can use the same routes as browser tabs.

Important lifecycle behavior:

    - Closing the pool window closes only the pool window.
    - Closing the main window closes the pool window if open, shuts down
      NiceGUI, and exits the desktop app.
    - In web mode, clicking Open Pool opens a browser tab.

For a production CloudScope web server, the in-memory AppStore must become
per-user/session scoped. This demo uses one AppStore because it is a local
proof-of-concept.
"""

from __future__ import annotations

import multiprocessing
import os
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, Literal

from nicegui import app, ui


DEFAULT_DESKTOP_HOST = "127.0.0.1"
DEFAULT_WEB_HOST = "0.0.0.0"
DEFAULT_DESKTOP_URL_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def find_free_port() -> int:
    """Find an available localhost TCP port.

    Returns:
        Available TCP port bound on localhost.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((DEFAULT_DESKTOP_HOST, 0))
        return int(sock.getsockname()[1])


AppMode = Literal["desktop", "web"]
SelectionSource = Literal["main", "pool", "system"]



@dataclass(frozen=True)
class DemoSettings:
    """Runtime settings loaded from environment variables.

    Attributes:
        mode: Desktop or web mode.
        host: Host interface used by the NiceGUI server.
        port: TCP port used by the NiceGUI server.
        url_host: Hostname used when creating local pywebview URLs.
    """

    mode: AppMode
    host: str
    port: int
    url_host: str


@dataclass(frozen=True)
class SelectionState:
    """Shared selection state.

    Attributes:
        file: Selected file identifier.
        channel: Selected channel index.
        roi_id: Selected ROI identifier.
        source: Component that most recently changed the selection.
    """

    file: str | None = None
    channel: int | None = None
    roi_id: int | None = None
    source: SelectionSource = "system"


@dataclass(frozen=True)
class PoolDataChangedEvent:
    """Event announcing that pool data changed.

    Attributes:
        version: Monotonic pool data version.
        source: Component that requested the mutation.
        changed_rows: Optional row ids that changed.
    """

    version: int
    source: SelectionSource
    changed_rows: list[int] | None = None


@dataclass(frozen=True)
class UpdatePoolRowIntent:
    """Intent requesting a mutation of one pool row.

    Attributes:
        pool_row_id: Row id to update.
        updates: Column/value updates to apply.
        source: Component that emitted the intent.
    """

    pool_row_id: int
    updates: dict[str, object]
    source: SelectionSource


class AppStore:
    """Shared in-memory app state for this proof-of-concept."""

    def __init__(self) -> None:
        """Initialize demo state."""
        self.selection = SelectionState()
        self.pool_rows = self._make_demo_rows()
        self.pool_data_version = 0
        self._lock = threading.RLock()
        self._selection_subscribers: list[Callable[[SelectionState], None]] = []
        self._pool_data_subscribers: list[Callable[[PoolDataChangedEvent], None]] = []

    def subscribe_selection(self, callback: Callable[[SelectionState], None]) -> None:
        """Subscribe to selection changes.

        Args:
            callback: Function called when selection changes.
        """
        with self._lock:
            self._selection_subscribers.append(callback)

    def subscribe_pool_data(
        self,
        callback: Callable[[PoolDataChangedEvent], None],
    ) -> None:
        """Subscribe to pool data changes.

        Args:
            callback: Function called when pool data changes.
        """
        with self._lock:
            self._pool_data_subscribers.append(callback)

    def set_selection(self, selection: SelectionState) -> None:
        """Set selection and notify subscribers.

        Args:
            selection: New selection state.
        """
        with self._lock:
            self.selection = selection
            subscribers = list(self._selection_subscribers)

        for callback in subscribers:
            callback(selection)

    def handle_update_pool_row_intent(self, intent: UpdatePoolRowIntent) -> None:
        """Apply one row update intent.

        Args:
            intent: Row update intent.
        """
        with self._lock:
            changed = False
            for row in self.pool_rows:
                if row["pool_row_id"] != intent.pool_row_id:
                    continue
                for column, value in intent.updates.items():
                    if column in row:
                        row[column] = value
                        changed = True
                row["last_source"] = intent.source
                changed = True
                break

            if not changed:
                return

            self.pool_data_version += 1
            event = PoolDataChangedEvent(
                version=self.pool_data_version,
                source=intent.source,
                changed_rows=[intent.pool_row_id],
            )
            subscribers = list(self._pool_data_subscribers)

        for callback in subscribers:
            callback(event)

    def mutate_first_row(self, source: SelectionSource) -> None:
        """Mutate the first row as a simple demo action.

        Args:
            source: Component that requested the mutation.
        """
        with self._lock:
            row = dict(self.pool_rows[0])
        self.handle_update_pool_row_intent(
            UpdatePoolRowIntent(
                pool_row_id=int(row["pool_row_id"]),
                updates={"value": int(row["value"]) + 1},
                source=source,
            )
        )

    def records(self) -> list[dict]:
        """Return current pool records.

        Returns:
            Copy of current row records.
        """
        with self._lock:
            return [dict(row) for row in self.pool_rows]

    def columns(self) -> list[dict]:
        """Return NiceGUI table columns.

        Returns:
            Column definitions for ui.table.
        """
        return [
            {
                "name": name,
                "label": name,
                "field": name,
                "align": "left",
                "sortable": True,
            }
            for name in self.records()[0]
        ]

    def _make_demo_rows(self) -> list[dict]:
        """Create demo pool rows.

        Returns:
            Demo row records.
        """
        rows: list[dict] = []
        for row_index in range(20):
            rows.append(
                {
                    "pool_row_id": row_index,
                    "file": f"file_{row_index % 5:03d}.tif",
                    "channel": row_index % 3,
                    "roi_id": row_index % 8,
                    "value": row_index,
                    "last_source": "system",
                }
            )
        return rows


class WindowLauncher:
    """Open the pool view as either a pywebview window or browser tab."""

    def __init__(self, settings: DemoSettings) -> None:
        """Initialize the launcher.

        Args:
            settings: Runtime demo settings.
        """
        self.mode = settings.mode
        self.url_host = settings.url_host
        self.port = settings.port
        self.pool_window = None

    def open_pool(self) -> None:
        """Open or focus the pool view."""
        if self.mode == "desktop":
            self._open_pool_window()
            return
        self._open_pool_tab()

    def _open_pool_window(self) -> None:
        """Open or focus the pywebview pool window."""
        if self.pool_window is not None:
            try:
                self.pool_window.show()
                return
            except Exception as exc:
                print(f"existing pool window was not usable: {exc}")
                self.pool_window = None

        url = f"http://{self.url_host}:{self.port}/pool"
        print(f"opening pool pywebview window: {url}")
        import webview

        self.pool_window = webview.create_window(
            "Pool",
            url=url,
            width=900,
            height=700,
        )

        def on_closed() -> None:
            """Clear the pool window reference when closed."""
            self.pool_window = None

        self.pool_window.events.closed += on_closed

    def _open_pool_tab(self) -> None:
        """Open the pool route in a browser tab."""
        ui.run_javascript("window.open('/pool', '_blank')")


class MainView:
    """Main demo view."""

    def __init__(self, store: AppStore, launcher: WindowLauncher) -> None:
        """Initialize the main view.

        Args:
            store: Shared app store.
            launcher: Pool launcher.
        """
        self.store = store
        self.launcher = launcher
        self.selection_label = None
        self.version_label = None
        self.table = None

    def build(self) -> None:
        """Build the main page."""
        ui.label("Main View").classes("text-h5")

        with ui.row():
            ui.button("Open pool", on_click=self.launcher.open_pool)
            ui.button(
                "Select from main",
                on_click=lambda: self.store.set_selection(
                    SelectionState("file_001.tif", 1, 7, "main")
                ),
            )
            ui.button(
                "Mutate first row from main",
                on_click=lambda: self.store.mutate_first_row("main"),
            )

        self.selection_label = ui.label()
        self.version_label = ui.label()

        self.table = ui.table(
            columns=self.store.columns(),
            rows=self.store.records(),
            row_key="pool_row_id",
            selection="single",
            pagination=10,
            on_select=self._on_table_select,
        ).classes("w-full")

        self.store.subscribe_selection(self._on_selection_changed)
        self.store.subscribe_pool_data(self._on_pool_data_changed)
        self._refresh_from_store()

    def _refresh_from_store(self) -> None:
        """Refresh UI from shared store."""
        self._on_selection_changed(self.store.selection)
        self._on_pool_data_changed(
            PoolDataChangedEvent(self.store.pool_data_version, "system", None)
        )

    def _on_table_select(self) -> None:
        """Push selected table row into shared selection."""
        if self.table is None or not self.table.selected:
            return
        row = self.table.selected[0]
        self.store.set_selection(
            SelectionState(
                file=str(row["file"]),
                channel=int(row["channel"]),
                roi_id=int(row["roi_id"]),
                source="main",
            )
        )

    def _on_selection_changed(self, selection: SelectionState) -> None:
        """Handle shared selection changes.

        Args:
            selection: New selection state.
        """
        if self.selection_label is None:
            return
        self.selection_label.text = (
            f"Selection: file={selection.file}, channel={selection.channel}, "
            f"roi_id={selection.roi_id}, source={selection.source}"
        )

    def _on_pool_data_changed(self, event: PoolDataChangedEvent) -> None:
        """Handle pool data changes by doing a full table refresh.

        Args:
            event: Pool data changed event.
        """
        if self.version_label is not None:
            self.version_label.text = (
                f"Pool version: {event.version}, source={event.source}, "
                f"changed_rows={event.changed_rows}"
            )
        if self.table is not None:
            self.table.rows = self.store.records()
            self.table.update()


class PoolView:
    """Pool demo view."""

    def __init__(self, store: AppStore) -> None:
        """Initialize the pool view.

        Args:
            store: Shared app store.
        """
        self.store = store
        self.selection_label = None
        self.version_label = None
        self.table = None

    def build(self) -> None:
        """Build the pool page."""
        ui.label("Pool View").classes("text-h5")

        with ui.row():
            ui.button(
                "Select from pool",
                on_click=lambda: self.store.set_selection(
                    SelectionState("file_002.tif", 2, 9, "pool")
                ),
            )
            ui.button(
                "Mutate first row from pool",
                on_click=lambda: self.store.mutate_first_row("pool"),
            )
            ui.button("Update selected row", on_click=self._update_selected_row)

        self.selection_label = ui.label()
        self.version_label = ui.label()

        self.table = ui.table(
            columns=self.store.columns(),
            rows=self.store.records(),
            row_key="pool_row_id",
            selection="single",
            pagination=10,
            on_select=self._on_table_select,
        ).classes("w-full")

        self.store.subscribe_selection(self._on_selection_changed)
        self.store.subscribe_pool_data(self._on_pool_data_changed)
        self._refresh_from_store()

    def _refresh_from_store(self) -> None:
        """Refresh UI from shared store."""
        self._on_selection_changed(self.store.selection)
        self._on_pool_data_changed(
            PoolDataChangedEvent(self.store.pool_data_version, "system", None)
        )

    def _on_table_select(self) -> None:
        """Push selected table row into shared selection."""
        if self.table is None or not self.table.selected:
            return
        row = self.table.selected[0]
        self.store.set_selection(
            SelectionState(
                file=str(row["file"]),
                channel=int(row["channel"]),
                roi_id=int(row["roi_id"]),
                source="pool",
            )
        )

    def _update_selected_row(self) -> None:
        """Update selected row through an intent-like object."""
        if self.table is None or not self.table.selected:
            ui.notify("Select one row first")
            return

        row = self.table.selected[0]
        self.store.handle_update_pool_row_intent(
            UpdatePoolRowIntent(
                pool_row_id=int(row["pool_row_id"]),
                updates={"value": int(row["value"]) + 10},
                source="pool",
            )
        )

    def _on_selection_changed(self, selection: SelectionState) -> None:
        """Handle shared selection changes.

        Args:
            selection: New selection state.
        """
        if self.selection_label is None:
            return
        self.selection_label.text = (
            f"Selection: file={selection.file}, channel={selection.channel}, "
            f"roi_id={selection.roi_id}, source={selection.source}"
        )

    def _on_pool_data_changed(self, event: PoolDataChangedEvent) -> None:
        """Handle pool data changes by doing a full table refresh.

        Args:
            event: Pool data changed event.
        """
        if self.version_label is not None:
            self.version_label.text = (
                f"Pool version: {event.version}, source={event.source}, "
                f"changed_rows={event.changed_rows}"
            )
        if self.table is not None:
            self.table.rows = self.store.records()
            self.table.update()


class OptionCDemoApp:
    """Minimal Multi-window demo app."""

    def __init__(self, settings: DemoSettings) -> None:
        """Initialize the demo.

        Args:
            settings: Runtime demo settings.
        """
        self.settings = settings
        self.mode = settings.mode
        self.host = settings.host
        self.port = settings.port
        self.url_host = settings.url_host
        self.store = AppStore()
        self.launcher = WindowLauncher(settings)

    def register_pages(self) -> None:
        """Register NiceGUI routes."""

        @ui.page("/")
        def main_page() -> None:
            """Render the main page."""
            MainView(self.store, self.launcher).build()

        @ui.page("/pool")
        def pool_page() -> None:
            """Render the pool page."""
            PoolView(self.store).build()

    def run(self) -> None:
        """Run the demo app."""
        self.register_pages()
        if self.mode == "desktop":
            self._run_desktop()
        else:
            self._run_web()

    def _run_web(self) -> None:
        """Run as a normal web app."""
        ui.run(
            host=self.host,
            port=self.port,
            native=False,
            reload=False,
            title="Option C Web Demo",
            storage_secret="multi-window-demo-secret",
        )

    def _run_desktop(self) -> None:
        """Run NiceGUI server in a thread and own pywebview windows manually."""
        server_thread = threading.Thread(
            target=self._run_server_for_desktop,
            daemon=True,
        )
        server_thread.start()

        self._wait_for_server()
        main_url = f"http://{self.url_host}:{self.port}/"
        print(f"opening main pywebview window: {main_url}")
        import webview

        main_window = webview.create_window(
            "Main",
            url=main_url,
            width=1000,
            height=750,
        )

        def on_main_closed() -> None:
            """Close pool window and shut down NiceGUI when the main window closes."""
            print("main window closed; closing pool window and shutting down NiceGUI")

            pool_window = self.launcher.pool_window
            if pool_window is not None:
                try:
                    pool_window.destroy()
                except Exception as exc:
                    print(f"Pool window destroy raised: {exc}")
                finally:
                    self.launcher.pool_window = None

            try:
                app.shutdown()
            except Exception as exc:
                print(f"NiceGUI shutdown raised: {exc}")

        main_window.events.closed += on_main_closed

        try:
            webview.start()
        finally:
            print("pywebview stopped; shutting down NiceGUI")
            try:
                app.shutdown()
            except Exception as exc:
                print(f"NiceGUI shutdown raised: {exc}")

    def _run_server_for_desktop(self) -> None:
        """Run NiceGUI server without opening a browser or native window."""
        ui.run(
            host=self.host,
            port=self.port,
            native=False,
            show=False,
            reload=False,
            title="Option C Desktop Demo Server",
            storage_secret="multi-window-demo-secret",
        )

    def _wait_for_server(self) -> None:
        """Wait briefly for the local server to start.

        This intentionally avoids adding an HTTP dependency. If the server is
        slower on a specific machine, increase the sleep.
        """
        time.sleep(1.0)


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable.

    Args:
        name: Environment variable name.
        default: Value used when the variable is unset.

    Returns:
        Parsed boolean value.
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_settings() -> DemoSettings:
    """Resolve runtime settings from environment variables.

    Environment variables:
        CLOUDSCOPE_DEMO_MODE: "desktop" or "web". Defaults to "desktop".
        CLOUDSCOPE_HOST: NiceGUI bind host. Defaults to 127.0.0.1 in desktop
            mode and 0.0.0.0 in web mode.
        CLOUDSCOPE_URL_HOST: Host used in pywebview URLs. Defaults to
            127.0.0.1.
        PORT: NiceGUI bind port. In desktop mode, a free port is selected when
            PORT is not set. In web mode, defaults to 8080.

    Returns:
        Runtime settings.
    """
    mode_value = os.getenv("CLOUDSCOPE_DEMO_MODE", "desktop").strip().lower()
    mode: AppMode = "web" if mode_value in {"web", "server", "browser"} else "desktop"

    default_host = DEFAULT_WEB_HOST if mode == "web" else DEFAULT_DESKTOP_HOST
    host = os.getenv("CLOUDSCOPE_HOST", default_host).strip()

    url_host = os.getenv("CLOUDSCOPE_URL_HOST", DEFAULT_DESKTOP_URL_HOST).strip()

    port_env = os.getenv("PORT")
    if port_env is None or not port_env.strip():
        port = DEFAULT_PORT if mode == "web" else find_free_port()
    else:
        port = int(port_env)

    return DemoSettings(mode=mode, host=host, port=port, url_host=url_host)


def main() -> None:
    """Run the demo."""
    settings = resolve_settings()
    print(
        "Multi-window demo settings: "
        f"mode={settings.mode}, host={settings.host}, "
        f"port={settings.port}, url_host={settings.url_host}"
    )
    OptionCDemoApp(settings=settings).run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
