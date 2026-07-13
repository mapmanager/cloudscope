# CloudScope GUI Rebuild / Reconnect State Roadmap

Planning document for improving how CloudScope saves and restores GUI state when
the NiceGUI client disconnects, reloads, returns to an existing server session, or
wakes after desktop sleep.

**Status:** living roadmap, partially implemented. Tickets 019–021 have landed
(see [Implemented so far](#implemented-so-far)); the remaining plan follows.
Sections below are annotated **[DONE]**, **[PARTIAL]**, or **[PLANNED]** so the
current state of the disconnect/reconnect system is clear.

**Related prior work:**

- `docs-dev/cursor_tickets/001_disconnect_reconnect_handoff.md` — original planning
- `docs-dev/cursor_tickets/002_reconnect_plotly_refresh_report.md` — empty 1D plots fix
- `docs-dev/cursor_tickets/003_session_reconnect_restore_report.md` — session snapshot implementation
- `docs-dev/cursor_tickets/019_plot_view_typed_state_pilot_report.md` — plot-view typed-state pilot
- `docs-dev/cursor_tickets/020_app_state_contract_and_raster_typed_state_report.md` — app-state contract + raster typed state
- `docs-dev/cursor_tickets/021_page_layout_chrome_restore_report.md` — page-level layout chrome restore

---

## Implemented so far

This section tracks landed work against the roadmap. The roadmap body below
remains the full plan.

- **Ticket 019 — plot-view typed-state pilot.** `PlotlyPlotDisplayOptions`
  gained `to_dict`/`from_dict`; `PlotlyPlotWidget.__init__` now takes a single
  `display_options`; `AcqAnalysisPlotViewState` and `SumIntensityPlotViewState`
  (incl. per-series visibility) own their blob shape.
- **Ticket 020 — app-state contract + raster typed state.**
  - `HomePageRestorableState` (selection, `primary_x_range`, `file_ids`) is the
    typed, JSON-safe app-level contract, built by
    `HomePageState.to_restorable_state()` and captured into
    `HomePageSessionSnapshot.app_state` on disconnect. Restore still reads live
    controller state; `app_state` is currently for diagnostics/serialization.
  - `HomePageChromeState` and `HomePageSessionSnapshot` gained
    `to_dict`/`from_dict`; `DebugView` now renders `snapshot.to_dict()` and
    stays thin.
  - `PlotlyRasterViewerDisplayOptions` gained `to_dict`/`from_dict`
    (`layout_margins_profile` excluded as a construction-time concern).
  - `PrimaryImageView` uses `PrimaryImageViewState` + `RasterViewport` instead
    of a loose blob; `ReferenceImageView` gained `ReferenceImageViewState`
    (display options only; viewport reset on reference reload).
  - Deferred (unchanged): moving restore delivery to true build time, and
    `HomePageChromeState` field cleanup / new page-chrome fields
    (`left_toolbar_open`, splitters, pool tab).
- **Ticket 021 — page-level layout restore.**
  - `HomePageChromeState` cleaned to real page chrome: kept `file_list_open`
    and `analysis_plot_open`; removed dead `reference_image_open` /
    `velocity_pool_open`; added `left_toolbar_active_view_id: str | None`
    (open ⇔ not `None`) and `right_pool_open: bool`. Capture via
    `HomePageChromeState.capture(...)`.
  - Splitter drag positions are **not** added to chrome — `SplitterManager`
    already persists them in `AppConfig`. Only the left-toolbar/right-pool
    open toggles (which `AppConfig` does not restore) live in chrome.
  - `LeftToolbarView(initial_active_view_id=...)` restores the active tab at
    build time (invalid/unknown ids collapse safely).
  - `VelocityPoolViewState(active_tab=...)` restores the right pool's
    Velocity/Peaks tab via the standard `export/apply_session_state` path.
  - Chrome is applied at build time from `runtime.session_snapshot.chrome`;
    true build-time delivery of per-view blobs remains deferred.

---

## Problem

CloudScope is a NiceGUI app. The **backend/runtime state survives** across client
rebuilds, but the **GUI widgets are rebuilt from scratch**.

When a browser client disconnects and reconnects, reloads the page, or returns to
a running CloudScope web server session, the app must restore the user's working
context as much as possible.

Today:

- **Global app state restore works reasonably well** (file, channel, ROI,
  analysis row, primary x-range).
- **Per-view GUI chrome restore is fragile** — loose dict blobs, manual
  export/apply parity, build-with-defaults-then-patch.

This will not scale across `src/cloudscope/views/` (~20 views) without a cleaner
pattern.

---

## Why This Matters

### Desktop (native) mode

End users do not know CloudScope is a web-connected NiceGUI app. If their computer
sleeps and they return, the GUI should restore their working context.

Analogy: a word processor where the user is on page 25 of 100 with the cursor in
the middle of a paragraph. After sleep/wake, they must not land back on page 1 with
the cursor reset.

### Web mode

Slow/intermittent network, tab reload, and returning to an existing server session
are the same class of problem: **GUI rebuild against surviving runtime state**.

### Future: shareable view state

Once state is typed and serializable, the same machinery can support "share what
I'm looking at" URLs (see [Future: Shareable View State URLs](#future-shareable-view-state-urls)).

---

## Terminology (Use These Names)

The current code uses "reconnect" in several places, but the trigger is broader
than websocket disconnect.

| Term | Meaning |
|------|---------|
| **Cold build** | First `home_page()` build for a new `CloudScopeRuntime` (`runtime.initialized == False`). |
| **Runtime rebuild** | Page widgets rebuilt while runtime already exists (`runtime.initialized == True`). Triggers: websocket reconnect, tab reload, returning web client, desktop wake. |
| **Runtime rebuild with snapshot** | Runtime rebuild plus a captured `HomePageSessionSnapshot` from a prior disconnect. |
| **Server/process restart** | Python process restarted; in-memory runtime is gone. Only persisted config/data can help. |

**Important:** `was_initialized = runtime.initialized` in `home_page()` means
**runtime rebuild**, not specifically "websocket reconnect."

---

## Current Architecture

### What survives vs what is rebuilt

| Layer | Survives rebuild? | Location |
|-------|-------------------|----------|
| Controllers, event bus, loaded files, selection, x-range | Yes | `CloudScopeRuntime` → `HomePageController.state` |
| View/widget instances, NiceGUI elements, AG Grid/Plotly DOM | No | Rebuilt in `HomePage.build()` |
| Session snapshot (chrome + app_state + per-view blobs) | Yes (in memory only) | `runtime.session_snapshot: HomePageSessionSnapshot \| None` |

**Not survived:** a Python process restart clears the runtime registry, so the
in-memory `session_snapshot` is gone. Only persisted `AppConfig` (last path,
dark mode, splitter drag positions) helps after a restart.

### Runtime key / session identity

`get_current_runtime()` (`src/cloudscope/runtime.py`) resolves user context, computes
a registry key, and returns or creates a `CloudScopeRuntime`:

```python
user_context, app_config = resolve_runtime_context()
key = runtime_key_from_user_context(user_context)  # currently user_context.user_id
return get_registry().get_or_create(key, lambda: _build_runtime(...))
```

- **Native/local:** key is the local OS user; multiple browser clients can share one runtime.
- **Remote/demo web:** `get_or_create_demo_session_id()` uses NiceGUI browser storage
  for a browser-stable session id; same runtime while server process is alive.
- **Server restart:** runtime registry is empty; cold build only.

### Lifecycle: disconnect capture **[DONE]**

`HomePage.build()` registers `ui.context.client.on_disconnect()`. The current
handler captures chrome, app-level state, and per-view blobs into one snapshot,
then hides every view (which unsubscribes its events):

```python
def _on_client_disconnect() -> None:
    runtime = get_current_runtime()
    left_toolbar = left_toolbar_ref['value']
    active_left_tab = left_toolbar.active_view_id if left_toolbar is not None else None
    runtime.session_snapshot = HomePageSessionSnapshot(
        chrome=HomePageChromeState.capture(
            file_list_open=panel_open_state['file_list'],
            analysis_plot_open=panel_open_state['analysis_plot'],
            left_toolbar_active_view_id=(
                active_left_tab.value if active_left_tab is not None else None
            ),
            right_pool_open=splitter_manager.is_right_pool_open(),
        ),
        app_state=runtime.home_page_controller.state.to_restorable_state(),
        views=view_manager.collect_session_state(),
    )
    for view_id in view_manager.view_ids():
        view_manager.get(view_id).on_hide()
```

`view_manager.collect_session_state()` calls every registered view's
`export_session_state()` and keys the resulting blob by `ViewId` value.

### Lifecycle: rebuild and restore **[DONE]**

`home_page()` (`src/cloudscope/pages/home_page.py`):

```python
runtime = get_current_runtime()
was_initialized = runtime.initialized          # True => runtime rebuild
runtime.initialize_once()

if was_initialized:
    runtime.reconnect_build_in_progress = True

page.build(reconnect=was_initialized)

if was_initialized:
    snapshot = runtime.session_snapshot or HomePageSessionSnapshot.empty()
    runtime.home_page_controller.publish_session_reconnect_restore(snapshot)

runtime.reconnect_build_in_progress = False
```

During runtime rebuild:

1. `reconnect_build_in_progress` suppresses normal view hydrate in
   `BaseView.on_show()` (it only syncs the selection cache + subscribes; it does
   not call `refresh_from_state()`).
2. Fresh view instances are constructed. **Page chrome is restored at build
   time** from `runtime.session_snapshot.chrome` (file-list/analysis-plot open,
   left-toolbar active tab via `LeftToolbarView(initial_active_view_id=...)`,
   right-pool open). Per-view widget content is still built with defaults.
3. After build, `publish_session_reconnect_restore(snapshot)` first ensures the
   selection's lazy pixel data is loaded, then publishes one
   `HomePageSessionReconnectRestore` carrying controller selection + x-range +
   `acq_image` and the per-view blobs (`view_session`).
4. Each visible view's `_on_session_reconnect_restore()` applies its blob (when
   `selection_guard_matches`) via `apply_session_state()`, then calls
   `on_session_reconnect_restore()` for a data refresh.

Note: `HomePageSessionSnapshot.app_state` is captured but **not** consumed on
restore — step 3 reads live `HomePageController.state`. `app_state` exists today
for diagnostics/serialization and future shareable-state URLs.

### Three "restore-needed" signals (current complexity) **[PARTIAL]**

1. `was_initialized` — runtime already bootstrapped
2. `reconnect_build_in_progress` — suppress normal hydrate during build
3. `session_snapshot` — optional chrome + app_state + per-view blobs from disconnect

Still present; documented here but not yet renamed. See
[Why not rewrite the whole architecture](#why-not-rewrite-the-whole-architecture).

---

## State Architecture Overview

The classes that **store** reconnect state and the methods that **refresh** it
from that state. All serializable state carries `schema_version`
(`VIEW_SESSION_SCHEMA_VERSION`) and is validated with `require_keys` /
`require_schema_version` on read.

### Classes that store state

| Class | Module | Holds | Serializable |
|-------|--------|-------|--------------|
| `HomePageState` | `controllers/home_page_controller.py` | Live app state: `file_ids`, `selection`, `acq_image_list`, `visible_file_ids_provider`, `primary_x_range` | No (mixed runtime objects). Projects to serializable via `to_restorable_state()` / `to_debug_dict()` |
| `HomePageRestorableState` | `session_state.py` | App-level serializable subset: `selection`, `primary_x_range`, `file_ids` | Yes (`to_dict`/`from_dict`) |
| `HomePageChromeState` | `session_state.py` | Page shell chrome: `file_list_open`, `analysis_plot_open`, `left_toolbar_active_view_id`, `right_pool_open` | Yes |
| `HomePageSessionSnapshot` | `session_state.py` | `chrome` + `app_state` + `views: dict[str, dict]` | Yes |
| `PrimaryImageViewState` + `RasterViewport` | `views/primary_image_view.py` | z/t, contrast, LUT, display options, viewport | Yes |
| `ReferenceImageViewState` | `views/reference_image_view.py` | raster display options | Yes |
| `AcqAnalysisPlotViewState` | `views/acq_analysis_plot_view.py` | display options, `events_visible` | Yes |
| `SumIntensityPlotViewState` | `views/sum_intensity_plot_view.py` | display options, per-series visibility | Yes |
| `VelocityPoolViewState` | `views/velocity_pool_view.py` | active tab (velocity/peaks) | Yes |
| `PlotlyPlotDisplayOptions` | `nicewidgets/plotly_plot/display_options.py` | 1D plot display flags + theme | Yes |
| `PlotlyRasterViewerDisplayOptions` | `nicewidgets/raster_viewer/frontend/plotly_display_options.py` | raster display flags + theme (`layout_margins_profile` excluded) | Yes |

`FileListTreeView` still exports an **untyped dict blob**
(`expanded_group_ids` + `selection_guard`); it is the last non-typed per-view
state (see [Phase 5](#phase-5-filelisttreeview)).

### Where state lives at rest vs on the wire

- **At rest between disconnect and rebuild:** `runtime.session_snapshot`
  (a `HomePageSessionSnapshot`, in memory on the runtime).
- **On the wire during restore:** `HomePageSessionReconnectRestore` event
  (`events/session_reconnect.py`) carries controller selection/x-range/acq_image
  plus `view_session` (the snapshot's per-view blobs).

### Methods that refresh state

| Path | Method(s) | When |
|------|-----------|------|
| Capture | `BaseView.export_session_state()` (overridden per typed view) → `ViewManager.collect_session_state()` | On disconnect |
| Global restore | `HomePageController.publish_session_reconnect_restore()` → `_publish_session_reconnect_restore_event()` | After rebuild |
| Per-view restore | `BaseView._on_session_reconnect_restore()` → `apply_session_state()` + `on_session_reconnect_restore()` | On restore event |
| Chrome restore | `HomePage.build()` reading `session_snapshot.chrome` | At build time |
| Normal (non-reconnect) refresh | `BaseView.on_show()` → `refresh_from_state()` | Cold build / show |

---

## Runtime Flow: Client Disconnect → Rebuild

End-to-end path for a websocket disconnect/reconnect (the same path handles tab
reload, returning web client, and desktop wake — any **runtime rebuild**).

1. **NiceGUI disconnect signal.** The browser socket drops. NiceGUI fires the
   `ui.context.client.on_disconnect(...)` callback registered in
   `HomePage.build()` → `_on_client_disconnect()`.
2. **Capture snapshot.** `_on_client_disconnect()` writes
   `runtime.session_snapshot = HomePageSessionSnapshot(chrome=..., app_state=...,
   views=collect_session_state())`. Chrome is read from live page layout;
   `app_state` from `HomePageController.state.to_restorable_state()`; each view
   contributes a blob via `export_session_state()`.
3. **Hide views.** Every view's `on_hide()` runs → `unsubscribe_events()`. The
   runtime, controllers, event bus, and loaded `AcqImageList` all survive.
4. **Reconnect → new page request.** On reconnect NiceGUI re-invokes the
   `@ui.page("/")` `home_page()` function for the new client connection.
5. **Detect runtime rebuild.** `was_initialized = runtime.initialized` is `True`
   (runtime already bootstrapped). `initialize_once()` is idempotent and does not
   reload data. `runtime.reconnect_build_in_progress = True`.
6. **Build with chrome restore.** `page.build(reconnect=True)` reads
   `runtime.session_snapshot.chrome` and constructs the shell in its restored
   layout (file-list panel, analysis-plot panel, left-toolbar active tab,
   right-pool open). Views are constructed and built; because
   `reconnect_build_in_progress` is set, `on_show()` suppresses the normal
   hydrate and only syncs the selection cache + subscribes (including to
   `HomePageSessionReconnectRestore`).
7. **Publish one restore event.**
   `publish_session_reconnect_restore(snapshot)` stashes the snapshot, ensures
   the selection's lazy pixel data is loaded, then publishes
   `HomePageSessionReconnectRestore` with controller selection/x-range/acq_image
   and `view_session` (the per-view blobs).
8. **Views hydrate.** Each subscribed view runs
   `_on_session_reconnect_restore()`: refresh selection cache, cache x-range,
   look up its blob by `ViewId`, and if `selection_guard_matches` apply it via
   `apply_session_state()`; then `on_session_reconnect_restore()` refreshes data
   (e.g. re-slice the raster, re-render the plot). Post-build-only state (Plotly
   viewport, AG Grid expanded rows) is applied here because it needs the DOM.
9. **Clear the flag.** `runtime.reconnect_build_in_progress = False`.

### Build-time vs post-build restore

Two restore timings coexist by design:

- **Build-time (chrome):** page layout is applied while widgets are constructed,
  straight from `session_snapshot.chrome`. No DOM round-trip needed.
- **Post-build (per-view blobs):** widgets are built with defaults, then patched
  by the restore event because some state (Plotly viewport, AG Grid rows) only
  exists once the browser element is live, and because the restore event is the
  single point that also delivers the freshly-loaded `acq_image`.

### Why not rewrite the whole architecture

"Rewriting the architecture" would mean inverting the post-build path: reading
each view's saved blob **before** constructing the view and feeding it into
constructors, so widgets are born in their restored state instead of
built-then-patched. That is a large, cross-cutting change (every view
constructor, the build order, and the restore event plumbing) and is risky to
verify. Page-level layout does **not** need it: chrome is applied at build time
from `runtime.session_snapshot.chrome`, which already exists. So we get the
layout restore we want without that rewrite. Constructor-time restore of
per-view content remains a **[PLANNED]**, opt-in, incremental step (see
[Phase 6](#phase-6-reduce-blobguard-machinery)), not a prerequisite.

---

## What Works Today (Keep Simple)

**Global app state** — restore via controller + event, not view blobs:

| State | Source on restore | Status |
|-------|-------------------|--------|
| `file_id`, `channel`, `roi_id`, `analysis_name` | `HomePageController.state` → `HomePageSessionReconnectRestore` event | Works |
| `primary_x_range` | `HomePageState.primary_x_range` on reconnect event | Works |
| Page panel chrome (file-list/analysis-plot open) | `HomePageChromeState` at build time | Works |
| Left-toolbar active tab | `HomePageChromeState.left_toolbar_active_view_id` → `LeftToolbarView(initial_active_view_id=...)` | Works |
| Right pool open + active tab | `HomePageChromeState.right_pool_open` + `VelocityPoolViewState` | Works |
| Plot display options + series visibility | `AcqAnalysisPlotViewState` / `SumIntensityPlotViewState` blobs | Works |
| Primary image z/t, contrast, display options, viewport | `PrimaryImageViewState` + `RasterViewport` | Works |
| Reference image display options | `ReferenceImageViewState` | Works |

Do **not** redesign this first. Keep global selection and x-range on the controller.

---

## What Is Wrong Today (Per-View State)

**Progress:** the loose-blob anti-pattern below has been replaced by typed state
in `AcqAnalysisPlotView`, `SumIntensityPlotView` (incl. series visibility),
`PrimaryImageView`, `ReferenceImageView`, and `VelocityPoolView`. What remains:

- `FileListTreeView` still exports an **untyped dict blob** (`expanded_group_ids`).
- Even for typed views, `apply_session_state()` is still applied **post-build**
  via the restore event rather than fed into constructors — the
  `selection_guard` / `require_keys` machinery still runs on the read path.

The description below documents the original anti-pattern (now mostly retired)
so the remaining `FileListTreeView` cleanup keeps the same target shape.

### Anti-pattern: loose dict blobs **[PARTIAL — FileListTreeView remains]**

Every view with reconnect state used to implement a hand-written export/apply pair.

Example (historical) from `SumIntensityPlotView`, now typed via
`SumIntensityPlotViewState`:

```135:164:src/cloudscope/views/sum_intensity_plot_view.py
    def export_session_state(self) -> dict[str, Any]:
        ...
        return {
            'schema_version': VIEW_SESSION_SCHEMA_VERSION,
            'selection_guard': selection_guard_from_selection(self.current_selection),
            'display_options': display_options,
        }

    def apply_session_state(self, data: dict[str, Any]) -> None:
        require_schema_version(data)
        require_keys(data, 'selection_guard', 'display_options')
        self._apply_plot_display_options(PlotlyPlotDisplayOptions(**data['display_options']))
```

Problems:

- State shape is not obvious from types; every field must be mirrored in export,
  apply, and `require_keys`.
- Widgets are built with **hardcoded defaults**, then state is **patched afterward**
  via setters.
- Adding a new UI toggle requires touching 4+ places per view.
- `selection_guard` adds validation complexity; mismatches skip blob apply silently
  (warning log only).

Same pattern in `AcqAnalysisPlotView`, `PrimaryImageView`, `FileListTreeView`.

### Anti-pattern: scattered Plotly constructor args **[DONE — ticket 019]**

`PlotlyPlotWidget.__init__` previously took primitive flags (`show_legend`,
`show_x_axis_labels`, `show_y_axis_labels`) and rebuilt a
`PlotlyPlotDisplayOptions` internally, so the constructor and the reconnect blob
used different representations of the same state.

Resolved: `PlotlyPlotWidget.__init__` now takes a single
`display_options: PlotlyPlotDisplayOptions | None`, and the plot views build/read
that same dataclass for reconnect. One representation, one source of truth.

### Incomplete restore: Sum Intensity series visibility **[DONE — ticket 019]**

`SumIntensityPlotView` registers custom context-menu series via
`_sum_intensity_series_menu_items()`:

- Derivative of df/f0
- Peak width traces (10, 25, 50, 75, 90)
- Onsets, Peaks
- Diameter overlay

Each `PlotlySeriesMenuItem` has a `series_name` and `default_visible`. The widget
tracks mutable visibility in `PlotlyPlotWidget._series_visibility: dict[str, bool]`.

Resolved: `SumIntensityPlotViewState` now captures per-series visibility, so
after reconnect the user's series toggle choices are restored alongside display
options. `_on_series_visibility_changed()` no longer uses `del visible` (the
`del` was removed per the KISS convention); the handler ignores the unused value
without deleting it.

### Two restore mechanisms (split responsibility)

| Mechanism | Carries | Applied by |
|-----------|---------|------------|
| Reconnect **event** | selection, x-range, acq_image | `BaseView._on_session_reconnect_restore()` |
| View **blob** | display options, expanded groups, z/t/contrast/viewport | `apply_session_state()` per view |

This split is conceptually OK (global vs local), but the blob side is too manual.

---

## Proposed Direction

### Principle: typed state, build-time restore first

1. **Define typed state dataclasses** for widget and view chrome.
2. **Mutate typed state during normal runtime** (user toggles update the state object).
3. **Capture typed state on disconnect** (serialize or store object on snapshot).
4. **Pass typed state into constructors on rebuild** where possible.
5. **Post-build apply only for browser-dependent state** (AG Grid expansion, Plotly
   viewport after element exists).

### Global vs per-view state (unchanged split)

| Category | Owner | Restore path |
|----------|-------|--------------|
| file, channel, ROI, analysis_name, primary_x_range | Controller / `HomePageState` | Reconnect event |
| plot display options, series visibility | View / widget typed state | Build-time config |
| primary image z/t, contrast, display options | View typed state | Build-time + post-build viewport |
| tree expanded group ids | View typed state | Post-build (AG Grid rows must exist) |
| page panel open/closed | `HomePageChromeState` | Build-time chrome flags |

---

## Proposed State Types

**Implementation note:** the pilot did **not** introduce a wrapper
`PlotlyPlotState`. Instead each view owns its own state dataclass
(`SumIntensityPlotViewState`, `AcqAnalysisPlotViewState`) that embeds
`PlotlyPlotDisplayOptions` plus view-specific fields (series visibility,
`events_visible`). The `PlotlyPlotState` sketch below is kept for context; treat
the per-view dataclasses as the shipped shape. `PrimaryImageViewState`,
`RasterViewport`, and `ReferenceImageViewState` are **[DONE]**;
`FileListTreeViewState` is **[PLANNED]**.

### Plotly plot state (nicewidgets + plot views)

```python
@dataclass(slots=True)
class PlotlyPlotState:
    display_options: PlotlyPlotDisplayOptions
    series_visibility: dict[str, bool] = field(default_factory=dict)
```

`PlotlyPlotWidget` should:

- Accept `initial_state: PlotlyPlotState | None` (or `display_options=` directly) in
  `__init__`, not scattered primitive flags.
- Own and export `PlotlyPlotState` via `export_state() -> PlotlyPlotState`.
- Update `series_visibility` when user toggles context-menu items.

**Before (current):**

```python
self._plot = PlotlyPlotWidget(
    theme="dark" if self._initial_dark_mode else "light",
    show_legend=False,
    show_x_axis_labels=True,
    show_y_axis_labels=False,
    ...
)
self._plot.register_series_menu_items(self._sum_intensity_series_menu_items())
# ... later on reconnect ...
self._apply_plot_display_options(PlotlyPlotDisplayOptions(**data['display_options']))
```

**After (proposed):**

```python
plot_state = restored_state.plot if restored_state else PlotlyPlotState(
    display_options=PlotlyPlotDisplayOptions(
        show_legend=False,
        show_x_axis_labels=True,
        show_y_axis_labels=False,
        theme="dark" if dark_mode else "light",
    ),
    series_visibility=default_sum_intensity_series_visibility(),
)
self._plot = PlotlyPlotWidget(
    initial_state=plot_state,
    on_series_visibility_changed=self._on_series_visibility_changed,
    ...
)
self._plot.register_series_menu_items(self._sum_intensity_series_menu_items())
```

Static menu item definitions (`PlotlySeriesMenuItem`) remain static. Mutable state
is the visibility map.

### Sum Intensity view state (pilot)

```python
@dataclass(slots=True)
class SumIntensityPlotViewState:
    plot: PlotlyPlotState
```

Pilot view because it has both generic Plotly state and view-specific series menu
extensions.

### Primary image view state

```python
@dataclass(slots=True)
class RasterViewport:
    x: tuple[float, float]
    y: tuple[float, float]

@dataclass(slots=True)
class PrimaryImageViewState:
    z: int
    t: int
    contrast_auto_per_slice: bool
    manual_contrast_lut: str | None
    manual_contrast_range: tuple[float, float] | None
    display_options: PlotlyRasterViewerDisplayOptions
    viewport: RasterViewport | None
```

- State is typed and serializable.
- `viewport` application may still be **post-build** because the Plotly raster element
  must exist in the browser.

Current loose blob in `PrimaryImageView.export_session_state()` should become this
typed object.

### File list tree view state

```python
@dataclass(slots=True)
class FileListTreeViewState:
    expanded_group_ids: tuple[str, ...]
```

AG Grid expansion depends on row data existing. Likely remains **post-build apply**,
but should not remain an unstructured dict blob.

---

## Build-Time vs Post-Build Restore

| State | Restore timing | Reason |
|-------|----------------|--------|
| Plotly display options | Build-time (constructor) | Python-owned, no DOM needed |
| Plotly series visibility | Build-time (constructor) | Python-owned |
| Primary image z/t, contrast, LUT | Build-time (view fields) | Python-owned |
| Primary image viewport | Post-build | Browser Plotly element must exist |
| AG Grid expanded rows | Post-build | Grid rows must exist |
| Global selection, x-range | Reconnect event (after build) | Controller-owned; views subscribe |

---

## Home Page Build: Clarity Improvements (Near-Term, Low Risk) **[PLANNED]**

Even before the state refactor, improve transparency in `home_page()` and
`HomePage.build()`:

1. **Rename or comment** `was_initialized` → document as "runtime rebuild, not only
   websocket reconnect."
2. **Rename or comment** `reconnect_build_in_progress` → "suppress normal view
   hydrate until restore event."
3. **Comment** that `session_snapshot` is optional; controller state is the primary
   restore source even when snapshot is empty.
4. **Comment** that returning web clients and tab reloads hit the same code path as
   disconnect/reconnect when runtime persists.

These may be comments only if renames are deferred.

---

## Implementation Phases

### Phase 0: Document and stabilize (this roadmap) **[DONE]**

- Agree on terminology and state split.
- Manual reconnect test checklist (already passing for core path).
- No behavior change required.

### Phase 1: Plotly widget API cleanup **[DONE — ticket 019]**

**Files:** `src/nicewidgets/plotly_plot/widget.py`, `display_options.py`, new
`plot_state.py` (or extend `display_options.py`).

- Introduce `PlotlyPlotState`.
- Change `PlotlyPlotWidget.__init__` to accept `initial_state` or `display_options`.
- Add `export_state() -> PlotlyPlotState`.
- Preserve existing behavior for callers not yet migrated.

### Phase 2: Pilot — `SumIntensityPlotView` **[DONE — ticket 019]**

**Files:** `src/cloudscope/views/sum_intensity_plot_view.py`, tests.

- Introduce `SumIntensityPlotViewState`.
- Save/restore series visibility (derivative, peak widths, onsets, peaks, diameter).
- Pass restored state into `PlotlyPlotWidget` at build time.
- Remove or replace `del visible` in `_on_series_visibility_changed`; visibility
  mutates formal state.
- Reduce `export_session_state` / `apply_session_state` to thin wrappers around typed
  state (or eliminate if build-time restore is sufficient).

### Phase 3: `AcqAnalysisPlotView` **[DONE — ticket 019]**

**Files:** `src/cloudscope/views/acq_analysis_plot_view.py`.

- Reuse `PlotlyPlotState`.
- Add view-specific fields (e.g. `events_visible`) to a small
  `AcqAnalysisPlotViewState` wrapper.

### Phase 4: `PrimaryImageView` **[DONE — ticket 020]**

**Files:** `src/cloudscope/views/primary_image_view.py`,
`src/nicewidgets/raster_viewer/frontend/plotly_display_options.py`.

- Introduce `PrimaryImageViewState` + `RasterViewport`. Done.
- `PlotlyRasterViewerDisplayOptions` gained `to_dict`/`from_dict`. Done.
- `ReferenceImageView` gained `ReferenceImageViewState` (display options; viewport
  resets on reference reload). Done.
- z/t/contrast/display options + post-build viewport apply. Done (restore still
  delivered post-build via the event, not constructor).

### Phase 5: `FileListTreeView` **[PLANNED — remaining loose blob]**

**Files:** `src/cloudscope/views/file_list_tree_view.py`,
`src/nicewidgets/tree_widget/tree_widget.py`.

- Introduce `FileListTreeViewState`.
- Post-build expanded-group restore.
- Re-verify interaction with main's selection/scroll behavior (tickets 016/017).

### Phase 6: Reduce blob/guard machinery **[PLANNED]**

**Files:** `src/cloudscope/session_state.py`, `src/cloudscope/views/base_view.py`,
`src/cloudscope/events/session_reconnect.py`.

- Replace dict blobs with typed snapshot objects where possible.
- Re-evaluate `selection_guard` — if snapshot is tied to the disconnecting client
  and event selection comes from the same runtime, guard may be unnecessary or should
  compare against controller state at capture time, not per-view cache.
- Simplify `apply_session_state()` to post-build-only cases.

### Phase 7: Extend pattern to remaining views **[PARTIAL]**

Apply the same pattern to other `src/cloudscope/views/` as needed. Done for
`VelocityPoolView` (ticket 021, active-tab state). Remaining candidates that can
hold user-editable runtime state: `VelocityAnalysisView`, `DiameterAnalysisView`,
`SumIntensityAnalysisView`, `EventAnalysisView`. Views that consume only app-level
selection (`ImageToolbarView`, `LoadSaveView`, `FooterView`, `HeaderView`) and
transient/modal views (`SumIntensityPoolPlotConfig`, `VelocityPoolPlotConfig`,
`DebugView`, `AppConfigView`, `AppInfoView`) do not need saved state. Do not build
a giant framework first; copy the proven pilot pattern per view.

---

## Future: Shareable View State URLs

**Not in scope for immediate reconnect work.** Design typed state so this becomes
feasible later.

### User story

1. User 1 configures CloudScope (file, analysis, x-range, plot toggles, viewport).
2. User 1 clicks "Copy View Link."
3. CloudScope serializes global app state + per-view typed states.
4. User 2 opens the URL and sees the same scientific context.

### Deployment context

- Local absolute paths like `/Users/cudmore/...` are **not** portable and should not
  be shared.
- Docker-compose deployments with a mounted shared data volume **can** share paths
  meaningfully between users on the same server.
- Future user accounts and group-shared storage make this powerful: User 1 and User 2
  in the same group reference the same dataset identifiers/paths.

### Requirements for shareable state (design now, implement later)

- Typed, versioned, JSON-serializable state objects.
- Separate **shareable** state from **local/session-only** state (e.g. scroll
  position of a local panel, client id).
- Use stable file/dataset identifiers, not ephemeral absolute paths where possible.
- Snapshot schema version field (already started with `VIEW_SESSION_SCHEMA_VERSION`).

---

## Friction and Red Flags

### Do not over-engineer

- The `PlotlyPlotWidget` + `SumIntensityPlotView` pilot is done; keep copying that
  proven per-view pattern instead of building a generic "view state framework".
- Do not refactor all remaining views at once.

### `app_state` is captured but not consumed on restore

`HomePageSessionSnapshot.app_state` (a `HomePageRestorableState`) is written on
disconnect but restore reads live `HomePageController.state`. This is intentional
today, but it means the serialized app-state contract can silently drift from the
real restore source. Before it is used for restore or shareable URLs, add a test
that asserts `to_restorable_state()` matches what the reconnect event actually
publishes.

### Do not continue expanding dict blobs

`FileListTreeView` is the last untyped blob. Every new toggle added to
export/apply/`require_keys` is ongoing maintenance debt — convert it (Phase 5)
rather than growing it.

### AG Grid tree remains special

Expanded rows and scroll-into-view (main tickets 016/017) interact with reconnect
tree restore. Manual verification required after changes; unit tests alone are
insufficient for AG Grid behavior.

### Runtime naming obscures intent

- `get_current_runtime()` is really get-or-create-by-user-key.
- `initialized` is really bootstrap-completed.
- `reconnect_build_in_progress` is really runtime-rebuild-suppress-hydrate.

Renaming is optional but comments are mandatory for future maintainers.

### Multi-client / stale handler risk

Multiple NiceGUI clients can share one runtime and event bus. View instances from
prior client builds may leave subscriptions if lifecycle is wrong. The reconnect
restore event path should be audited when simplifying state (subscription idempotency
in `BaseView.on_show()` / `on_hide()`).

### Process restart vs runtime rebuild

Typed in-memory snapshot does **not** survive server restart. Persisted `AppConfig`
(last path, dark mode, etc.) is a separate concern. Do not conflate them in this
roadmap.

### Guard mismatch warnings

Observed intermittently; did not block core restore in manual tests. Likely related
to per-view `current_selection` vs controller `_state.selection` at capture time, or
stale view handlers. When a guard mismatches, the view's blob is skipped (warning
log only) and only the global event state is applied. Re-evaluate when blob
machinery is simplified (Phase 6); do not chase without typed state in place.

### Chrome restore assumes the same left-toolbar tab set

`left_toolbar_active_view_id` restore relies on the rebuilt `LeftToolbarView`
containing the same tab ids. Unknown/removed ids collapse safely (no active tab),
but a renamed `ViewId` would silently drop the restored tab. Keep `ViewId` values
stable or bump `VIEW_SESSION_SCHEMA_VERSION`.

---

## Manual Verification Checklist (Post-Change)

After each phase, manual test (native or web with real data):

1. Load folder, select file, expand tree, select analysis row (`sum_intensity`).
2. Set x-range (e.g. 2–4 s).
3. Toggle plot context-menu series (derivative, peak widths, diameter).
4. Adjust primary image contrast/viewport if testing primary image phase.
5. Trigger disconnect (network off, or sleep/wake on desktop).
6. Reconnect.
7. Verify:
   - file + analysis row selected
   - x-range restored
   - series visibility restored (after Phase 2)
   - expanded tree groups restored (after Phase 5)
   - primary image viewport restored (after Phase 4)
   - no selection flash on user row click (tree, after Phase 5)

---

## Summary

| Done | Remaining |
|------|-----------|
| Controller selection + x-range on reconnect event | `FileListTreeView` loose blob → typed `FileListTreeViewState` (Phase 5) |
| Page chrome (panels, left tab, right pool) restored at build time | Reduce `selection_guard` / `require_keys` machinery (Phase 6) |
| Plotly ctor takes a single `PlotlyPlotDisplayOptions` (ticket 019) | Optional: constructor-time restore of per-view content |
| Plot views typed: `AcqAnalysisPlotViewState`, `SumIntensityPlotViewState` (incl. series visibility) | Analysis views typed state (Phase 7): velocity/diameter/sum-intensity/event |
| Raster views typed: `PrimaryImageViewState` + `RasterViewport`, `ReferenceImageViewState` | Assert `app_state` matches the reconnect event before using it for restore/sharing |
| `VelocityPoolView` active-tab state (ticket 021) | Future: shareable view state URLs |
| App-state contract: `HomePageRestorableState`, `HomePageSessionSnapshot.to_dict/from_dict` | Rename `was_initialized` / `reconnect_build_in_progress` (comments in place) |

**Next implementation target:** convert `FileListTreeView` to a typed
`FileListTreeViewState` (Phase 5), keeping post-build expansion apply and
re-verifying main tickets 016/017 tree selection/scroll behavior in the browser.
