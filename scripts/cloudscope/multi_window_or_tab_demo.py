"""NiceGUI demo for a shared main view and pool view.

This demo is designed to work in both NiceGUI desktop/native mode and
web/server mode.

Native desktop mode:
    uv run python scripts/nicewidgets/multi_window_or_tab_demo.py --native

Web/server mode:
    uv run python scripts/nicewidgets/multi_window_or_tab_demo.py --web

Environment variable mode:
    CLOUDSCOPE_DEMO_NATIVE=true uv run python scripts/nicewidgets/multi_window_or_tab_demo.py
    CLOUDSCOPE_DEMO_NATIVE=false uv run python scripts/nicewidgets/multi_window_or_tab_demo.py

The demo has two routes:

    /       Main view.
    /pool   Pool view.

In native=True mode, the pool route opens in a second pywebview window.
In native=False mode, the pool route opens in a second browser tab.

The shared state is intentionally simple:

    SelectionState
    PoolDataChangedEvent
    UpdatePoolRowIntent
    AppStore-owned pandas DataFrame

The DataFrame is not passed through events. Events only announce that shared
state changed. Each view refreshes from the shared AppStore.
"""

from __future__ import annotations

import argparse
import os
import uuid
from dataclasses import dataclass
from typing import Callable, Literal

import pandas as pd
import webview
from nicegui import app, ui

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

SelectionSource = Literal["main", "pool", "system"]


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
    """Event announcing that shared pool data changed.

    Attributes:
        version: Monotonic pool data version.
        source: Component that requested the mutation.
        changed_rows: Optional pool row ids that changed.
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
    """Shared app state for one desktop app or one web user/session."""

    def __init__(self, store_key: str) -> None:
        """Initialize the store.

        Args:
            store_key: Unique key identifying this store.
        """
        self.store_key = store_key
        self.selection = SelectionState()
        self.df = self._make_demo_dataframe()
        self.pool_data_version = 0
        self._selection_subscribers: list[Callable[[SelectionState], None]] = []
        self._pool_data_subscribers: list[
            Callable[[PoolDataChangedEvent], None]
        ] = []

    def subscribe_selection(self, callback: Callable[[SelectionState], None]) -> None:
        """Subscribe to selection changes.

        Args:
            callback: Function called when selection changes.
        """
        self._selection_subscribers.append(callback)

    def subscribe_pool_data(
        self,
        callback: Callable[[PoolDataChangedEvent], None],
    ) -> None:
        """Subscribe to pool data changes.

        Args:
            callback: Function called when pool data changes.
        """
        self._pool_data_subscribers.append(callback)

    def set_selection(self, selection: SelectionState) -> None:
        """Set the shared selection and notify subscribers.

        Args:
            selection: New selection state.
        """
        self.selection = selection
        for callback in list(self._selection_subscribers):
            callback(selection)

    def handle_update_pool_row_intent(self, intent: UpdatePoolRowIntent) -> None:
        """Apply a row update intent to the shared DataFrame.

        Args:
            intent: Row update intent.
        """
        row_mask = self.df["pool_row_id"] == intent.pool_row_id
        if not row_mask.any():
            return

        for column, value in intent.updates.items():
            if column in self.df.columns:
                self.df.loc[row_mask, column] = value

        self.df.loc[row_mask, "last_source"] = intent.source
        self.pool_data_version += 1

        self._emit_pool_data_changed(
            PoolDataChangedEvent(
                version=self.pool_data_version,
                source=intent.source,
                changed_rows=[intent.pool_row_id],
            )
        )

    def mutate_first_row(self, source: SelectionSource) -> None:
        """Mutate the first row as a simple demo action.

        Args:
            source: Component that requested the mutation.
        """
        if self.df.empty:
            return

        pool_row_id = int(self.df.iloc[0]["pool_row_id"])
        current_value = int(self.df.iloc[0]["value_00"])
        self.handle_update_pool_row_intent(
            UpdatePoolRowIntent(
                pool_row_id=pool_row_id,
                updates={"value_00": current_value + 1},
                source=source,
            )
        )

    def records(self) -> list[dict]:
        """Return current pool data as row records.

        Returns:
            Current DataFrame as a list of dictionaries.
        """
        return self.df.to_dict("records")

    def columns(self) -> list[dict]:
        """Return NiceGUI table column definitions.

        Returns:
            NiceGUI table columns for the current DataFrame.
        """
        return [
            {
                "name": column,
                "label": column,
                "field": column,
                "align": "left",
                "sortable": True,
            }
            for column in self.df.columns
        ]

    def _emit_pool_data_changed(self, event: PoolDataChangedEvent) -> None:
        """Notify subscribers that pool data changed.

        Args:
            event: Pool data changed event.
        """
        for callback in list(self._pool_data_subscribers):
            callback(event)

    def _make_demo_dataframe(self) -> pd.DataFrame:
        """Create a demo DataFrame.

        Returns:
            Demo DataFrame with 500 rows and 50 columns.
        """
        rows: list[dict] = []
        for row_index in range(500):
            row = {
                "pool_row_id": row_index,
                "file": f"file_{row_index % 10:03d}.tif",
                "channel": row_index % 3,
                "roi_id": row_index % 20,
                "accept": row_index % 2 == 0,
                "last_source": "system",
            }
            for col_index in range(44):
                row[f"value_{col_index:02d}"] = row_index + col_index
            rows.append(row)

        return pd.DataFrame(rows)


class AppStoreRegistry:
    """Registry for per-session AppStore instances."""

    def __init__(self) -> None:
        """Initialize an empty store registry."""
        self._stores: dict[str, AppStore] = {}

    def get_store(self, store_key: str) -> AppStore:
        """Get or create a store by key.

        Args:
            store_key: Store key.

        Returns:
            Shared AppStore for the key.
        """
        if store_key not in self._stores:
            self._stores[store_key] = AppStore(store_key)
        return self._stores[store_key]


class PoolLauncher:
    """Open the pool route as a native window or browser tab."""

    def __init__(self, native: bool, host: str, port: int) -> None:
        """Initialize the launcher.

        Args:
            native: Whether the app is running in NiceGUI native mode.
            host: Host to open the pool view on.
            port: Port to open the pool view on.
        """
        self.native = native
        self.host = host
        self.port = port
        self.pool_window = None

    def open_pool(self) -> None:
        """Open or focus the pool view."""
        print(f'open_pool: native={self.native}, host={self.host}, port={self.port}')
        if self.native:
            self._open_native_pool_window()
        else:
            self._open_browser_pool_tab()

    def _open_native_pool_window(self) -> None:
        """Open or focus the native pool window."""
        url = f"http://{self.host}:{self.port}/pool"
        print(f"opening native pool window: {url}")

        if self.pool_window is not None:
            try:
                print(f"trying existing pool window: {self.pool_window}")
                self.pool_window.restore()
                self.pool_window.show()
                return
            except Exception as exc:
                print(f"existing pool window was not usable: {exc}")
                self.pool_window = None

        try:
            print("before create_window")

            window = webview.create_window(
                "CloudScope Pool",
                url=url,
                width=1200,
                height=800,
            )

            print(f"after create_window: {window}")

            window.show()
            print("after window.show()")

        except Exception as exc:
            self.pool_window = None
            print(f"failed to open native pool window: {exc}")
            ui.notify(f"Failed to open pool window: {exc}", type="negative")
            return

        self.pool_window = window

        def on_closed() -> None:
            """Clear the pool window reference when closed."""
            self.pool_window = None

        window.events.closed += on_closed
        
    def _open_browser_pool_tab(self) -> None:
        """Open the pool route in a new browser tab."""
        ui.run_javascript("window.open('/pool', '_blank')")


class MainView:
    """Main application view."""

    def __init__(self, store: AppStore, pool_launcher: PoolLauncher) -> None:
        """Initialize the main view.

        Args:
            store: Shared app store.
            pool_launcher: Launcher used to open the pool view.
        """
        self.store = store
        self.pool_launcher = pool_launcher
        self.selection_label = None
        self.pool_data_label = None
        self.table = None

    def build(self) -> None:
        """Build the main view UI."""
        ui.label("Main View").classes("text-h5")

        with ui.row():
            ui.button("Open pool", on_click=self.pool_launcher.open_pool)
            ui.button(
                "Select file_001 / ch 1 / roi 7",
                on_click=lambda: self.store.set_selection(
                    SelectionState(
                        file="file_001.tif",
                        channel=1,
                        roi_id=7,
                        source="main",
                    )
                ),
            )
            ui.button(
                "Mutate first row from main",
                on_click=lambda: self.store.mutate_first_row("main"),
            )

            ui.button(
                "debug",
                on_click=lambda: print(f'app.native.main_window:{app.native.main_window}'),
            )

        self.selection_label = ui.label()
        self.pool_data_label = ui.label()

        self.table = ui.table(
            columns=self.store.columns(),
            rows=self.store.records()[:25],
            row_key="pool_row_id",
            selection="single",
            pagination=25,
            on_select=self._on_table_select,
        ).classes("w-full")

        self.store.subscribe_selection(self._on_selection_changed)
        self.store.subscribe_pool_data(self._on_pool_data_changed)
        self._refresh_from_store()

    def _refresh_from_store(self) -> None:
        """Refresh the view from the current shared store."""
        self._on_selection_changed(self.store.selection)
        self._on_pool_data_changed(
            PoolDataChangedEvent(
                version=self.store.pool_data_version,
                source="system",
                changed_rows=None,
            )
        )

    def _on_table_select(self) -> None:
        """Update shared selection when the main table selection changes."""
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
            f"Selection: file={selection.file}, "
            f"channel={selection.channel}, "
            f"roi_id={selection.roi_id}, "
            f"source={selection.source}"
        )

    def _on_pool_data_changed(self, event: PoolDataChangedEvent) -> None:
        """Handle shared pool data changes.

        Args:
            event: Pool data changed event.
        """
        if self.pool_data_label is not None:
            self.pool_data_label.text = (
                f"Pool data version: {event.version}, "
                f"source={event.source}, "
                f"changed_rows={event.changed_rows}"
            )

        if self.table is not None:
            self.table.update_rows(
                self.store.records()[:25],
                clear_selection=False,
            )


class PoolView:
    """Standalone pool view."""

    def __init__(self, store: AppStore) -> None:
        """Initialize the pool view.

        Args:
            store: Shared app store.
        """
        self.store = store
        self.selection_label = None
        self.pool_data_label = None
        self.table = None

    def build(self) -> None:
        """Build the pool view UI."""
        ui.label("Pool View").classes("text-h5")

        with ui.row():
            ui.button(
                "Select file_002 / ch 2 / roi 9",
                on_click=lambda: self.store.set_selection(
                    SelectionState(
                        file="file_002.tif",
                        channel=2,
                        roi_id=9,
                        source="pool",
                    )
                ),
            )
            ui.button(
                "Mutate first row from pool",
                on_click=lambda: self.store.mutate_first_row("pool"),
            )
            ui.button(
                "Update selected row",
                on_click=self._update_selected_row,
            )

        self.selection_label = ui.label()
        self.pool_data_label = ui.label()

        self.table = ui.table(
            columns=self.store.columns(),
            rows=self.store.records(),
            row_key="pool_row_id",
            selection="single",
            pagination=25,
            on_select=self._on_table_select,
        ).classes("w-full")

        self.store.subscribe_selection(self._on_selection_changed)
        self.store.subscribe_pool_data(self._on_pool_data_changed)
        self._refresh_from_store()

    def _refresh_from_store(self) -> None:
        """Refresh the view from the current shared store."""
        self._on_selection_changed(self.store.selection)
        self._on_pool_data_changed(
            PoolDataChangedEvent(
                version=self.store.pool_data_version,
                source="system",
                changed_rows=None,
            )
        )

    def _on_table_select(self) -> None:
        """Update shared selection when the pool table selection changes."""
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
        """Emit a row update intent for the selected pool row."""
        if self.table is None or not self.table.selected:
            ui.notify("Select one pool row first")
            return

        row = self.table.selected[0]
        pool_row_id = int(row["pool_row_id"])
        current_value = int(row["value_00"])

        self.store.handle_update_pool_row_intent(
            UpdatePoolRowIntent(
                pool_row_id=pool_row_id,
                updates={"value_00": current_value + 10},
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
            f"Selection: file={selection.file}, "
            f"channel={selection.channel}, "
            f"roi_id={selection.roi_id}, "
            f"source={selection.source}"
        )

    def _on_pool_data_changed(self, event: PoolDataChangedEvent) -> None:
        """Handle shared pool data changes.

        Args:
            event: Pool data changed event.
        """
        if self.pool_data_label is not None:
            self.pool_data_label.text = (
                f"Pool data version: {event.version}, "
                f"source={event.source}, "
                f"changed_rows={event.changed_rows}"
            )

        if self.table is not None:
            self.table.update_rows(
                self.store.records(),
                clear_selection=False,
            )


class MultiWindowOrTabDemoApp:
    """Demo application with shared main and pool views."""

    def __init__(self, native: bool, host: str, port: int) -> None:
        """Initialize the demo app.

        Args:
            native: Whether to run in NiceGUI native mode.
            host: Host to open the pool view on.
            port: Port to open the pool view on.
        """
        self.native = native
        self.host = host
        self.port = port
        self.registry = AppStoreRegistry()
        self.pool_launcher = PoolLauncher(
            native=native,
            host=host,
            port=port,
        )

    def register_pages(self) -> None:
        """Register app routes."""

        @ui.page("/")
        def main_page() -> None:
            """Render the main page."""
            store = self._get_current_store()
            MainView(store, self.pool_launcher).build()

        @ui.page("/pool")
        def pool_page() -> None:
            """Render the pool page."""
            store = self._get_current_store()
            PoolView(store).build()

    def run(self) -> None:
        """Run the NiceGUI app."""
        self.register_pages()

        ui.run(
            host=self.host,
            port=self.port,
            native=self.native,
            reload=False,
            title="CloudScope Multi-Window/Tab Demo",
            storage_secret="cloudscope-multi-window-demo-secret",
        )

    def _get_current_store(self) -> AppStore:
        """Resolve the current shared store.

        Returns:
            AppStore for desktop-local mode or current web user/session.
        """
        if self.native:
            return self.registry.get_store("desktop-local")

        if "cloudscope_demo_user_id" not in app.storage.user:
            app.storage.user["cloudscope_demo_user_id"] = str(uuid.uuid4())

        return self.registry.get_store(app.storage.user["cloudscope_demo_user_id"])


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--native",
        action="store_true",
        help="Run in NiceGUI native desktop mode.",
    )
    mode.add_argument(
        "--web",
        action="store_true",
        help="Run in browser/server mode.",
    )
    return parser.parse_args()


def resolve_native_mode(args: argparse.Namespace) -> bool:
    """Resolve native mode from CLI arguments and environment.

    Args:
        args: Parsed command-line arguments.

    Returns:
        True for native mode, False for web/server mode.
    """
    if args.native:
        return True

    if args.web:
        return False

    env_value = os.getenv("CLOUDSCOPE_DEMO_NATIVE", "true").strip().lower()
    return env_value in {"1", "true", "yes", "on"}


def main() -> None:
    """Run the demo application."""
    args = parse_args()
    native = resolve_native_mode(args)
    MultiWindowOrTabDemoApp(
        native=native,
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
    ).run()

if __name__ in {"__main__", "__mp_main__"}:
    main()