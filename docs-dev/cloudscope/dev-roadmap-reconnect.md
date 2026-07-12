# CloudScope GUI Rebuild / Reconnect State Roadmap

Planning document for improving how CloudScope saves and restores GUI state when
the NiceGUI client disconnects, reloads, returns to an existing server session, or
wakes after desktop sleep.

**Status:** planning only — no implementation in this document.

**Related prior work:**

- `docs-dev/cursor_tickets/001_disconnect_reconnect_handoff.md` — original planning
- `docs-dev/cursor_tickets/002_reconnect_plotly_refresh_report.md` — empty 1D plots fix
- `docs-dev/cursor_tickets/003_session_reconnect_restore_report.md` — session snapshot implementation

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
| Per-view chrome snapshot (if captured) | Yes (in memory) | `runtime.session_snapshot` |

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

### Lifecycle: disconnect capture

`HomePage.build()` registers `ui.context.client.on_disconnect()`:

```941:955:src/cloudscope/pages/home_page.py
        def _on_client_disconnect() -> None:
            runtime = get_current_runtime()
            runtime.session_snapshot = HomePageSessionSnapshot(
                chrome=HomePageChromeState.from_panel_open(panel_open_state),
                views=view_manager.collect_session_state(),
            )
            ...
            for view_id in view_manager.view_ids():
                view_manager.get(view_id).on_hide()
```

Each view's `export_session_state()` contributes a dict blob. Views call
`on_hide()` → `unsubscribe_events()`.

### Lifecycle: rebuild and restore

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

1. `reconnect_build_in_progress` suppresses normal view hydrate in `BaseView.on_show()`.
2. Fresh view instances are constructed and built with hardcoded defaults.
3. `HomePageSessionReconnectRestore` event publishes controller state + view blobs.
4. Each view's `_on_session_reconnect_restore()` applies blob (if guard matches) and
   calls `on_session_reconnect_restore()` for data refresh.

### Three "restore-needed" signals (current complexity)

1. `was_initialized` — runtime already bootstrapped
2. `reconnect_build_in_progress` — suppress normal hydrate during build
3. `session_snapshot` — optional per-view blobs from disconnect

These should be documented and eventually simplified/renamed for clarity.

---

## What Works Today (Keep Simple)

**Global app state** — restore via controller + event, not view blobs:

| State | Source on restore | Status |
|-------|-------------------|--------|
| `file_id`, `channel`, `roi_id`, `analysis_name` | `HomePageController.state` → `HomePageSessionReconnectRestore` event | Works |
| `primary_x_range` | `HomePageState.primary_x_range` on reconnect event | Works |
| Page panel chrome (file list open, etc.) | `HomePageChromeState` from snapshot | Works |

Do **not** redesign this first. Keep global selection and x-range on the controller.

---

## What Is Wrong Today (Per-View State)

### Anti-pattern: loose dict blobs

Every view with reconnect state implements a hand-written export/apply pair.

Example from `SumIntensityPlotView`:

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

### Anti-pattern: scattered Plotly constructor args

`PlotlyPlotWidget.__init__` takes primitive flags:

```python
show_legend: bool = True
show_x_axis_labels: bool = False
show_y_axis_labels: bool = False
```

Then internally builds:

```python
self._display_options = PlotlyPlotDisplayOptions(
    theme=self._theme,
    show_legend=bool(show_legend),
    show_x_axis_labels=bool(show_x_axis_labels),
    show_y_axis_labels=bool(show_y_axis_labels),
)
```

But views already save/restore `PlotlyPlotDisplayOptions` as a dataclass. The
constructor and the reconnect blob use **different representations of the same state**.

### Incomplete restore: Sum Intensity series visibility

`SumIntensityPlotView` registers custom context-menu series via
`_sum_intensity_series_menu_items()`:

- Derivative of df/f0
- Peak width traces (10, 25, 50, 75, 90)
- Onsets, Peaks
- Diameter overlay

Each `PlotlySeriesMenuItem` has a `series_name` and `default_visible`. The widget
tracks mutable visibility in `PlotlyPlotWidget._series_visibility: dict[str, bool]`.

**Current export saves only `PlotlyPlotDisplayOptions`. It does not save series
visibility.** After reconnect, user's series toggle choices are lost even when
display options restore.

`_on_series_visibility_changed()` uses `del visible` because only `series_name`
is needed for y2 label refresh — a sign that visibility state is not formally owned
by the view.

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

## Home Page Build: Clarity Improvements (Near-Term, Low Risk)

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

### Phase 0: Document and stabilize (this roadmap)

- Agree on terminology and state split.
- Manual reconnect test checklist (already passing for core path).
- No behavior change required.

### Phase 1: Plotly widget API cleanup

**Files:** `src/nicewidgets/plotly_plot/widget.py`, `display_options.py`, new
`plot_state.py` (or extend `display_options.py`).

- Introduce `PlotlyPlotState`.
- Change `PlotlyPlotWidget.__init__` to accept `initial_state` or `display_options`.
- Add `export_state() -> PlotlyPlotState`.
- Preserve existing behavior for callers not yet migrated.

### Phase 2: Pilot — `SumIntensityPlotView`

**Files:** `src/cloudscope/views/sum_intensity_plot_view.py`, tests.

- Introduce `SumIntensityPlotViewState`.
- Save/restore series visibility (derivative, peak widths, onsets, peaks, diameter).
- Pass restored state into `PlotlyPlotWidget` at build time.
- Remove or replace `del visible` in `_on_series_visibility_changed`; visibility
  mutates formal state.
- Reduce `export_session_state` / `apply_session_state` to thin wrappers around typed
  state (or eliminate if build-time restore is sufficient).

### Phase 3: `AcqAnalysisPlotView`

**Files:** `src/cloudscope/views/acq_analysis_plot_view.py`.

- Reuse `PlotlyPlotState`.
- Add view-specific fields (e.g. `events_visible`) to a small
  `AcqAnalysisPlotViewState` wrapper.

### Phase 4: `PrimaryImageView`

**Files:** `src/cloudscope/views/primary_image_view.py`.

- Introduce `PrimaryImageViewState` + `RasterViewport`.
- Build-time restore for z/t/contrast/display options.
- Post-build viewport apply.

### Phase 5: `FileListTreeView`

**Files:** `src/cloudscope/views/file_list_tree_view.py`,
`src/nicewidgets/tree_widget/tree_widget.py`.

- Introduce `FileListTreeViewState`.
- Post-build expanded-group restore.
- Re-verify interaction with main's selection/scroll behavior (tickets 016/017).

### Phase 6: Reduce blob/guard machinery

**Files:** `src/cloudscope/session_state.py`, `src/cloudscope/views/base_view.py`,
`src/cloudscope/events/session_reconnect.py`.

- Replace dict blobs with typed snapshot objects where possible.
- Re-evaluate `selection_guard` — if snapshot is tied to the disconnecting client
  and event selection comes from the same runtime, guard may be unnecessary or should
  compare against controller state at capture time, not per-view cache.
- Simplify `apply_session_state()` to post-build-only cases.

### Phase 7: Extend pattern to remaining views

Apply the same pattern to other `src/cloudscope/views/` as needed (velocity pool,
metadata editors, toolbars, etc.). Do not build a giant framework first; copy the
proven pilot pattern per view.

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

- Start with `PlotlyPlotWidget` + `SumIntensityPlotView` pilot.
- Do not build a generic "view state framework" before one view proves the design.
- Do not refactor all 20 views at once.

### Do not continue expanding dict blobs

Every new toggle added to export/apply/require_keys is ongoing maintenance debt.

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
stale view handlers. Re-evaluate when blob machinery is simplified; do not chase
without typed state in place.

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

| Keep simple | Refactor |
|-------------|----------|
| Controller selection + x-range on reconnect event | Loose dict blobs → typed state dataclasses |
| Page chrome from snapshot | Build-default-then-patch → build-from-restored-state |
| Runtime survives; widgets rebuild | Plotly scattered ctor args → `PlotlyPlotDisplayOptions` / `PlotlyPlotState` |
| | Sum Intensity series visibility in reconnect state |
| | Primary image typed state + viewport |
| | File tree typed expanded ids (post-build) |
| | Comments/clarity in `home_page()` rebuild path |
| | Future: shareable view state URLs |

**First implementation target:** `PlotlyPlotState` + `SumIntensityPlotView` pilot.
