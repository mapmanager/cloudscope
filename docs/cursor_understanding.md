# Cursor Understanding of CloudScope, acqstore, and nicewidgets

This document is Cursor's working understanding of the three packages in this
repository after reading `docs/cloudscope_architecture.md`, `docs/acqstore_api.md`,
`docs/nicewidgets_api.md`, `docs/cloudscope_packaging.md`, and the corresponding
source under `src/cloudscope`, `src/acqstore`, and `src/nicewidgets`.

It is intended to be handed back to ChatGPT so the user can verify that Cursor
understands the system before further development.

---

## 1. High-level architecture

CloudScope is a thin NiceGUI client. The repository hosts three cooperating
packages, all under `src/`:

```text
src/acqstore/      backend domain/data layer (AcqImage, ROIs, analysis, IO)
src/nicewidgets/   reusable NiceGUI widgets (PlotlyRasterViewer, EChartWidget, ImageToolbarWidget)
src/cloudscope/    app: pages, controllers, event bus, state, view shells
```

The architectural rule, paraphrased from `docs/cloudscope_architecture.md`:

```text
CloudScope stays thin.
acqstore owns acquisition/image/ROI/analysis interpretation.
nicewidgets owns reusable GUI widgets.
CloudScope orchestrates them.
```

Dependency direction (enforced by AGENTS.md):

```text
cloudscope  ──► acqstore
cloudscope  ──► nicewidgets
nicewidgets ─/► (never imports cloudscope)
acqstore    ─/► (never imports cloudscope or nicewidgets)
```

### Runtime entry point

`src/cloudscope/app.py`:

- Builds a `CloudScopeRunConfig` from environment variables
  (`CLOUDSCOPE_NATIVE`, `CLOUDSCOPE_REMOTE`, `CLOUDSCOPE_RELOAD`,
  `CLOUDSCOPE_HOST`, `CLOUDSCOPE_PORT`, `PORT`, `CLOUDSCOPE_STORAGE_SECRET`).
- Configures native pywebview window dimensions from `AppConfig` when
  `native=True`.
- Imports `cloudscope.pages.home_page` which registers `@ui.page('/')`.
- Calls `ui.run(...)`.

Per-client construction in `home_page()` creates a fresh `EventBus`,
`AppConfig` (loaded), `HomePageController`, `LoadSaveController`, then builds
a `HomePage`. `HomePage.build()` is the composition root: it creates the
remaining controllers (`AnalysisController`, `RoiController`), `TaskRunner`,
`ViewManager`, `SplitterManager`, and instantiates every view.

---

## 2. MVC mapping in the code

### Models (data / backend)

Owned by `acqstore`:

- `AcqImage` — root domain object for one file. Owns:
  - `images: BaseFileLoader` — raw image access and `ImageHeader` calibration.
  - `rois: RoiSet` — ROI CRUD (`create_rect_roi`, `delete`, `has_roi`,
    `get_roi_ids`, `get`).
  - `analysis_set: AcqAnalysisSet` — analyses keyed by
    `AnalysisKey(analysis_name, channel, roi_id)`.
  - Metadata sections (`ExperimentMetadata`, `ImageHeaderMetadata`).
  - `images.reference_image.get_plane(channel) -> ReferenceImagePlane`.
- `AcqImageList` — file collection with `get_files()`, `get_file_by_id()`,
  `get_default_selection()`, `get_schema_rows()`, and load/save with
  progress/cancel hooks.
- `BaseAnalysis` / `AnalysisPlotData` — analyses expose `get_plot_data()`
  returning a frozen `AnalysisPlotData(x, y, x_label, y_label, series_name)`.
  Today only `RadonVelocityAnalysis` has a concrete plot.
- `AnalysisRunContext(progress_callback, cancel_callback)` — cooperative
  progress/cancellation for long-running analyses.

### Views (NiceGUI)

`src/cloudscope/views/`. Every view derives from `BaseView` and has:

- A `ClassVar` `view_id: ViewId`.
- `build(parent)` (creates UI, sets `self.root`, calls `after_build()`).
- Lifecycle: `on_show()` / `on_hide()` driven by `set_visible(...)`.
- Auto-subscription to `AppBusyChanged`, `FileSelectionChanged`,
  `ChannelSelectionChanged`, `RoiSelectionChanged`.
- Cached `current_selection: PrimarySelection` and `current_acq_image`.
- Override hooks `subscribe_events()`, `refresh_from_state()`,
  `on_primary_selection_changed()`.
- `disable_when_busy: ClassVar[bool] = True` by default; image/plot/toolbar
  views set it `False` so they remain interactive during analysis.

Concrete views relevant to current work:

- `PrimaryImageView` — embeds `nicewidgets.PlotlyRasterViewer`; loads the
  selected plane via `acq_image.images.get_slice_data(channel)`, converts ROI
  bounds (acqstore `dim0/dim1`) into Plotly physical coordinates via
  `RasterGridSpec`, and pushes `RectRoiOverlay`s to the viewer.
- `ReferenceImageView` — embeds another `PlotlyRasterViewer` and consumes
  `acq_image.images.reference_image.get_plane(channel)`. ROI-selection-only
  changes are ignored by design.
- `AcqAnalysisPlotView` — embeds `nicewidgets.EChartWidget`; resolves an
  `AnalysisKey` from current selection, fetches `analysis.get_plot_data()`,
  pushes that into the chart.
- `ImageToolbarView` — adapts `nicewidgets.ImageToolbarWidget` intents
  (channel/ROI selection, ROI CRUD/edit buttons) into CloudScope
  `SelectChannelIntent` / `SelectRoiIntent` / `AddRoiIntent` /
  `DeleteRoiIntent` / `BeginEditRoiIntent` / `CancelEditRoiIntent` /
  `SubmitEditRoiIntent`.
- `LoadSaveView`, `FileListView`, `LeftToolbarView` (with `MetadataView`,
  `VelocityAnalysisView`, `AppConfigView`, `AppInfoView` as tab panels),
  `FooterView`, `HeaderView`, `TaskProgressDialogView`.

### Controllers

`src/cloudscope/controllers/`:

- `HomePageController` — owns `HomePageState` (file_ids, `PrimarySelection`,
  `AcqImageList`). Handles `SelectFileIntent`, `SelectChannelIntent`,
  `SelectRoiIntent`, `ApplyMetadataIntent`. Publishes `FileListChanged`,
  `FileSelectionChanged`, `ChannelSelectionChanged`, `RoiSelectionChanged`,
  `MetadataChanged`. Other controllers go through `HomePageController` when
  they need to mutate selection.
- `LoadSaveController` — handles `LoadPathIntent`, `SaveSelectedIntent`,
  `SaveAllIntent`; drives `AcqImageList` loads/saves through `TaskRunner`;
  publishes `FileListChanged` and `AppStatusChanged`.
- `AnalysisController` — handles `RunAnalysisIntent` and `CancelTaskIntent`;
  validates selection; runs `acq_image.analysis_set.run_analysis(...)` via
  `TaskRunner` with an `AnalysisRunContext`; publishes `AnalysisCompleted`
  and `AppStatusChanged`. Today only `AnalysisKind.RADON_VELOCITY` is
  supported; `AnalysisKind.DIAMETER` is declared but raises
  `NotImplementedError`.
- `RoiController` — handles `AddRoiIntent`, `DeleteRoiIntent`,
  `BeginEditRoiIntent`, `SubmitEditRoiIntent`, `CancelEditRoiIntent`,
  `ApplyRoi{FullWidth,FullHeight}Intent`. Mutates `acq_image.rois`, deletes
  dependent analyses via `acq_image.analysis_set.delete_roi(roi_id)`, selects
  the next ROI through `HomePageController.select_roi(...)`, and publishes
  `RoiChanged(RoiChangeKind, selection, removed_analysis_count)` and
  `RoiEditModeChanged`. ROI **edit geometry** intentionally raises a warning
  today; only edit-mode lifecycle is wired.

### Event bus

`EventBus` is a simple `defaultdict[type, list[handler]]` with type-hierarchy
dispatch via `type(event).__mro__`. Subscribers receive an `EventSubscription`
that they can `unsubscribe()`. `BaseView` tracks subscriptions and cleans them
up on `on_hide()`.

`events.py` defines three event taxonomies:

```text
IntentEvent  : SelectFileIntent, SelectChannelIntent, SelectRoiIntent,
               AddRoiIntent, DeleteRoiIntent, BeginEditRoiIntent,
               SubmitEditRoiIntent, CancelEditRoiIntent,
               ApplyRoi{FullWidth,FullHeight}Intent, ApplyMetadataIntent,
               LoadPathIntent, RemoveRecentPathIntent, ClearRecentPathsIntent,
               SaveSelectedIntent, SaveAllIntent, RunAnalysisIntent,
               CancelTaskIntent, ResetHomeLayoutIntent,
               SetHomeViewVisibleIntent
StateEvent   : FileListChanged, FileSelectionChanged,
               ChannelSelectionChanged, RoiSelectionChanged, RoiChanged,
               RoiEditModeChanged, MetadataChanged, TaskProgressChanged,
               AppBusyChanged, AnalysisCompleted, AppStatusChanged,
               RecentPathsChanged
```

### TaskRunner

`task_runner.TaskRunner` runs one task at a time on a worker thread, publishes
`AppBusyChanged(True/False)`, `TaskProgressChanged`, and `AppStatusChanged`,
and exposes a `TaskContext` to workers with `report_progress(...)`,
`is_cancelled()`, and `raise_if_cancelled()`. `CancelTaskIntent` is routed by
the relevant controller to `TaskRunner.cancel(task_kind, task_id)`.

---

## 3. Package boundary map

```text
HomePage (NiceGUI page)
  └─ HomePageController                ─► AppState ◄────────────┐
        ▲     ▲      ▲                                          │
        │     │      │                                          │
   intents events  reads/writes                                 │
        │     │      │                                          │
  Views ─┘     └──── EventBus ────► other controllers ──────────┘
   │              (Intent + State + Task events)
   │
   ├── PrimaryImageView ─► PlotlyRasterViewer (nicewidgets)
   │                         ├─ RasterViewService / pyramid (backend)
   │                         └─ PlotlyRoiOverlayLayer (Plotly.relayout shapes)
   ├── ReferenceImageView ─► PlotlyRasterViewer
   ├── AcqAnalysisPlotView ─► EChartWidget (nicewidgets)
   ├── ImageToolbarView ─► ImageToolbarWidget (nicewidgets)
   │
   └─ Backend access via:
         acq_image.images.get_slice_data(channel)
         acq_image.images.reference_image.get_plane(channel)
         acq_image.rois.*                # create_rect_roi, delete, get, ...
         acq_image.analysis_set.*        # get(key), run_analysis(...), delete_roi(roi_id)
         analysis.get_plot_data()        # -> AnalysisPlotData
```

This matches the architecture docs cleanly.

---

## 4. Selection model

`cloudscope.state.PrimarySelection(file_id, channel, roi_id)` is the canonical
selection unit. It flows in two directions:

```text
IntentEvent  (carries a selection snapshot for ROI/analysis intents)
StateEvent   (FileSelectionChanged carries the resolved selection + AcqImage)
```

`HomePageController.state` is the authoritative selection. `BaseView` caches
the current selection from selection state events so derived views can call
`get_selected_acq_image()`, `has_valid_primary_selection()`, etc.

For ROI mutation, controllers publish both:

- `RoiSelectionChanged` (selection moved) — via `HomePageController.select_roi(...)`.
- `RoiChanged(operation, selection, removed_analysis_count)` (model mutated).

The convention from the docs is enforced in code:

```text
Selection change       → BaseView.on_primary_selection_changed()
Model change w/o sel.  → custom subscription in a derived view
```

---

## 5. Long-running task pattern

```text
View
  ─► RunAnalysisIntent / LoadPathIntent / Save*Intent
  ─► Controller
        ─► TaskRunner.start(task_kind, task_label, worker, on_*)
              ─► AppBusyChanged(True)
              ─► worker(context)  (off main thread)
                    ─► acqstore API with progress_callback / should_cancel
                    ─► TaskProgressChanged events
              ─► AppBusyChanged(False)
              ─► AnalysisCompleted / FileListChanged / AppStatusChanged
```

`BaseView.disable_when_busy` disables most UI during a task. Views that must
remain interactive set `disable_when_busy = False` (e.g. `PrimaryImageView`,
`AcqAnalysisPlotView`, `ImageToolbarView`, `LeftToolbarView`,
`ReferenceImageView`).

---

## 6. Widget surfaces in nicewidgets

### `PlotlyRasterViewer`

`src/nicewidgets/raster_viewer/frontend/plotly_viewer.py` plus the
`backend/` (BackendImage, ImagePyramid, RasterViewService) and
`frontend/roi_overlay.py`.

Current public API (used by CloudScope):

```python
build() -> Element
async set_data(data: np.ndarray, *, grid: RasterGridSpec)
async apply_response(response)
async set_axis_ranges(*, x_min, x_max, y_min, y_max)
async set_x_axis_range(*, x_min, x_max)
async set_heatmap_contrast(*, zmin, zmax)
async set_heatmap_colorscale(colorscale)
set_rois(rois: Sequence[RectRoiOverlay])
select_roi(roi_id: int | None)
add_roi(roi: RectRoiOverlay)
delete_roi(roi_id: int)
```

Important implementation notes:

- The viewer owns a local `_plotly_dict` (the figure mirror). ROI overlay
  changes mutate `layout.shapes` in that dict and push **only** that subset to
  the browser using `Plotly.relayout` via `self._plot.client.run_javascript(js)`.
  Full image refresh uses NiceGUI's `self._plot.figure = ...; self._plot.update()`.
- ROI shapes are tagged with `name = "roi:<roi_id>"` so the viewer can update
  only its own shapes and leave others alone (`PlotlyRoiOverlayLayer.merge_shapes`).
- Pan/zoom/double-click events trigger backend re-renders via `RasterViewService`.

There is **no x/y line trace API yet** (matches user's next step #1).

### `EChartWidget`

`src/nicewidgets/echart_widget/widget.py`.

```python
set_line_data(*, x, y, x_label, y_label, series_name='series')
clear()
set_x_axis_limits(x_min, x_max)
reset_x_axis_limits()
apply()                  # internal: rebuilds full options dict and calls update()
build_options() -> dict
```

It is currently a single-series line widget; every change rebuilds the full
options dict and calls `container.update()`. There is **no datazoom**, **no
brush**, **no axis-range emission** (matches user's next step #2).

### `ImageToolbarWidget`

`src/nicewidgets/image_toolbar_widget/image_toolbar_widget.py`. Emits frozen
intent dataclasses for user gestures; provides `*_ext` setter methods that
update internal state without re-emitting intents. CloudScope adapts those to
app intents in `ImageToolbarView`.

---

## 7. AppConfig and packaging summary

- `AppConfig` (in `cloudscope/app_config.py`) holds JSON-persisted user
  prefs: recent paths, splitter values, home-view visibility,
  font sizes, window rect. Saves explicitly on shutdown when native; no
  hidden saves from splitter drags.
- `cloudscope/build_info.py` reads generated `_build_info.py` from the macOS
  packaging pipeline. Packaging scripts live in `packaging/macos/` and are
  documented in `docs/cloudscope_packaging.md`.
- `docs/cloudscope_packaging.md` is operational (release pipeline, signing,
  notarization, Docker mode) and orthogonal to the runtime architecture.

---

## 8. Sticking points and red flags

These are observations from reading the code, **not** required tickets; they
are flagged so they can be triaged.

### 8.1 `cloudscope/contracts` and `cloudscope/protocols` look orphaned

`src/cloudscope/contracts/` defines `AcqFileProtocol`, `AcqFileListProtocol`,
`AcqRoisProtocol`, `AcqImagesProtocol`, `AcqMetadataProtocol`,
`AcqAnalysisProtocol`, `AnalysisKind`, `MetadataFieldSchema`,
`TableColumnSchema`. `src/cloudscope/protocols.py` is a re-export shim that
calls itself "temporary." Searches show no production imports from either
module (`from cloudscope.contracts ...` and `from cloudscope.protocols ...`
return zero matches in `src/` and `tests/`).

Either:

- These were intentionally introduced to decouple cloudscope from concrete
  acqstore types, but the migration was never finished (most code still
  imports `AcqImage`, `RectROI`, `AnalysisKey`, etc. directly from acqstore), or
- They are dead code that should be removed.

This is a real architecture decision: keep them and wire them through, or
delete them. The architecture doc doesn't mention them.

### 8.2 Two `AnalysisKind` definitions exist

`cloudscope.events.AnalysisKind` is a `StrEnum` with `RADON_VELOCITY` and
`DIAMETER`. `cloudscope.contracts.common.AnalysisKind` is a separate enum
with the same purpose. The events one is the one actually used in runtime
code; the contracts one is currently unused. Source of confusion.

### 8.3 `ROI bounds vs. raster axes` is implicit

`acqstore` uses `dim0_start/dim0_stop` (rows) and `dim1_start/dim1_stop`
(columns). The `PlotlyRasterViewer` uses **row → plot x** and
**column → plot y** (so the Plotly x-axis is rows). CloudScope's
`_rect_roi_overlay_from_rect_roi` does the conversion:

```python
x0 = dim0_start * grid.dx
y0 = dim1_start * grid.dy
```

This is documented in `docs/acqstore_api.md`'s "ROI bounds" section, but the
fact that "plot x = image rows" is non-obvious and only enforced in
CloudScope view code. If the user's next step #1 adds line-plot traces over
the raster, the line `x` will be in **row-space physical units**, which must
be made explicit in the API.

### 8.4 ECharts widget redraws the whole options dict on every change

`EChartWidget.apply()` calls `container.options.clear() + update()` and
rebuilds the entire options dict. This will not scale well for fast incremental
updates (e.g. linked axis zoom). The architecture doc explicitly calls out the
opposite policy for the raster viewer ("avoid full plotly.update()"); the same
optimization needs to be considered for ECharts when datazoom / linked axes
arrive.

### 8.5 ROI geometry editing is stubbed

`SubmitEditRoiIntent`, `ApplyRoiFullWidthIntent`, `ApplyRoiFullHeightIntent`
all currently publish a "not implemented yet" warning. The intent surface is
there, but no draggable shape on the Plotly viewer is wired through. This is
flagged in the architecture doc under "Future ROI editing API" but is a real
gap that several wired-up UI buttons rely on.

### 8.6 `PrimaryImageView._refresh_raster_from_current_selection` race risk

Every selection change schedules a new coroutine via `asyncio.create_task`
without cancelling any in-flight loads. If the user switches files quickly,
several `_refresh_raster_async` coroutines can race; the last one to
`await self._viewer.set_data(...)` wins. Currently the impact is small (the
loads are short), but worth a guard once the raster pushes more data.

### 8.7 `AnalysisKind.DIAMETER` is declared but unimplemented

`AnalysisController._validate_intent` raises `NotImplementedError` for any
non-radon analysis. There is no diameter analysis class in
`src/acqstore/acq_image/analysis/` yet. Fine, just worth noting that the enum
advertises a feature that does not exist.

### 8.8 `LoadSaveController.task_runner` is patched after construction

In `home_page.py`:

```python
load_save_controller = LoadSaveController(event_bus, home_controller, app_config)
# ...
page = HomePage(...)
# Inside HomePage.build():
task_runner = TaskRunner(self.event_bus)
self.load_save_controller.task_runner = task_runner
```

`LoadSaveController` is constructed before its `task_runner` exists, then the
attribute is assigned later. Functional but fragile; ideally the runner is
constructed first and injected.

### 8.9 `events.py` is approaching 460 lines

The architecture doc already flags this and suggests a future split into
`events/` subpackage. Not urgent but listed.

### 8.10 Two views still consume `RoiChanged` and `MetadataChanged`

The doc's rule is that "selection change → BaseView path; model change w/o
selection → custom subscription." Current code follows the rule, but the set
of model-change subscribers (`FileListView`, `ImageToolbarView`,
`PrimaryImageView`, `AcqAnalysisPlotView`) needs to stay disciplined as new
views are added.

---

## 9. How the user's planned next steps map to this code

### 9.1 Step 1 — add x/y plot (trace) API to `PlotlyRasterViewer`

User's wording: "improve raster image to add api to add/delete/update an x/y
plot (using plotly dict traces, optimized for speed, e.g. do not call plotly()
update() but instead push changes to traces in the dict using javascript)."

Mapping to current code:

- The existing ROI overlay path is the right template:
  `PlotlyRoiOverlayLayer` mutates `layout.shapes` in the local figure dict
  and the viewer pushes only that subset with `Plotly.relayout(plotDiv, {shapes: ...})`
  (see `PlotlyRasterViewer._relayout_shapes`).
- Line traces are not shapes — they live in `figure.data[]`. The fast path is
  `Plotly.restyle`/`Plotly.addTraces`/`Plotly.deleteTraces`/`Plotly.extendTraces`
  depending on the operation. A symmetric layer (`PlotlyXyTraceLayer`?) is the
  right shape: own a dict of traces keyed by stable id, expose
  `set_traces(...)`, `add_trace(...)`, `update_trace(id, x, y, ...)`,
  `delete_trace(id)`, and emit a JS payload that mutates only those traces.
- The viewer would gain:

  ```python
  set_xy_traces(traces: Sequence[XyTrace])
  add_xy_trace(trace: XyTrace)
  update_xy_trace(trace_id: str, *, x=None, y=None, style=None)
  delete_xy_trace(trace_id: str)
  ```

- `set_data` (the raster update) must merge existing traces back into the new
  figure dict the same way it merges shapes (see `_build_initial_figure` and
  `_sync_roi_shapes_to_plotly_dict`).
- The trace ids must survive figure rebuilds (use `name = "xy:<id>"`, same
  pattern as `roi:<id>`).
- Coordinate space must be documented: plot x = image-row physical units,
  plot y = image-column physical units (matches 8.3 above).

This belongs in nicewidgets. CloudScope only adapts AnalysisPlotData (or some
new per-view payload) onto the new API.

### 9.2 Step 2 — click+drag x-axis zoom in `EChartWidget`, emit x-range

User's wording: "enable use click+drag to zoom into the echart widget/view
(ad api to nicewidgets for this and use the api in cloudscope/ so cloudscope
remains thin). once done, we need to link the emit signal of user set x-axis
in echart with the main app and listeners (like the raster view) need to set
their x-axis."

Mapping to current code:

- Today's ECharts options have **no `dataZoom`** entries and **no event
  subscriptions**. ECharts has two relevant mechanisms:
  - `dataZoom` (slider/inside) — gives drag-zoom on an axis and emits
    `datazoom` events.
  - `brush` — gives rubber-band selection and emits `brushSelected` events.
  - For click+drag rectangle zoom, the conventional approach is
    `toolbox.feature.dataZoom` plus `inside` zoom and listening to
    `datazoom` to read the new `xAxis` range.
- Widget API to add:

  ```python
  set_x_axis_zoom_enabled(enabled: bool)
  set_y_axis_zoom_enabled(enabled: bool)   # optional
  on_x_axis_range_changed: Callable[[float | None, float | None], None]
  # plus the existing set_x_axis_limits / reset_x_axis_limits
  ```

- The widget must keep emitting **only** user-driven changes. If CloudScope
  calls `set_x_axis_limits(...)` programmatically, that must not re-emit the
  callback (same `*_ext` pattern used by `ImageToolbarWidget`).
- Performance: the current `EChartWidget.apply()` rebuilds the whole options
  dict and calls `update()`. For linked-axis updates we probably want
  `ui.echart.run_chart_method('setOption', {...}, true)` (the second arg
  enables `notMerge=false`) or a direct JS push, similar to how the raster
  viewer uses `Plotly.relayout`. This is the same kind of optimization called
  out for the raster viewer in `docs/nicewidgets_api.md`.
- CloudScope side (a new app-level event, suggested in
  `docs/nicewidgets_api.md`):

  ```python
  @dataclass(frozen=True)
  class XAxisRangeChanged(StateEvent):
      source_view_id: ViewId
      x_min: float | None
      x_max: float | None
  ```

  A controller (`AxisLinkController`? or `HomePageController`) translates the
  widget callback into `XAxisRangeChanged(source_view_id=ACQ_ANALYSIS_PLOT)`.
  `PrimaryImageView` and any future view subscribe and call
  `viewer.set_x_axis_range(x_min, x_max)` if `event.source_view_id` is not
  their own (avoid feedback loops).
- The `PlotlyRasterViewer` already exposes `async set_x_axis_range(...)`,
  so the consumer side is partly there; it needs a synchronous façade or
  CloudScope needs to schedule the coroutine.

### 9.3 Step 3 — "there are other things"

Likely follow-up areas based on the gaps above:

- Wire actual ROI **geometry** edit (drag/resize the rectangle on the raster
  viewer, emit `on_roi_bounds_preview(roi_id, bounds)`, plumb through
  `RoiEditPreviewChanged` and `SubmitEditRoiIntent`/`CancelEditRoiIntent`).
- Decide on `cloudscope/contracts` (remove or actually use it).
- Add the diameter analysis class in acqstore, or remove
  `AnalysisKind.DIAMETER` until needed.
- Add `XAxisRangeChanged` (per the architecture doc) once axis linking lands.
- Consider migrating `EChartWidget.apply()` to incremental
  `Plotly.relayout`-style JS pushes for axis-range changes.

---

## 10. Suggested next 3–4 development steps (Cursor opinion)

These are roughly aligned with the user's plan but reordered/expanded:

1. **`PlotlyRasterViewer` x/y trace API (nicewidgets, then CloudScope use).**
   Add `PlotlyXyTraceLayer` mirroring `PlotlyRoiOverlayLayer`. Identify
   traces with `name = "xy:<trace_id>"`. Expose
   `set_xy_traces/add/update/delete`. Push only the affected traces via JS
   (`Plotly.addTraces/Plotly.restyle/Plotly.deleteTraces/Plotly.extendTraces`).
   Merge existing xy traces back when `set_data(...)` rebuilds the figure
   (analogous to `_sync_roi_shapes_to_plotly_dict`). Document the row→x,
   col→y coordinate convention on the API. CloudScope use: render an analysis
   line trace (or a calibration overlay) on top of the primary image.

2. **`EChartWidget` drag-zoom + x-range emission (nicewidgets).**
   Add `dataZoom` config (inside + optional slider), wire a NiceGUI event
   listener for ECharts `datazoom` (or `brushSelected` if preferred), expose
   a callback `on_x_axis_range_changed`, and add an `_ext` setter that updates
   range programmatically without re-emitting. Optimize `set_x_axis_limits`
   to use `run_chart_method('setOption', ..., notMerge=false)` instead of
   rebuilding the full options dict.

3. **App-level axis linking (CloudScope).**
   Add `XAxisRangeChanged(source_view_id, x_min, x_max)` state event. Add a
   small controller (`AxisLinkController` or extend `HomePageController`)
   that converts widget callbacks to the event. `PrimaryImageView` and
   `AcqAnalysisPlotView` subscribe and call their viewer's
   `set_x_axis_range(...)` only when `event.source_view_id != self.view_id`.
   Ensure the raster viewer's async `set_x_axis_range` is scheduled
   correctly from a sync subscriber. Test feedback-loop avoidance.

4. **Cleanup pass and ROI geometry edit groundwork.**
   - Decide and execute on `cloudscope/contracts` (delete or adopt).
   - Remove or stub-implement `AnalysisKind.DIAMETER` consistently.
   - Add the `on_roi_bounds_preview(roi_id, bounds)` callback on
     `PlotlyRasterViewer`, enable Plotly shape editing only when in edit
     mode, and feed previews into `RoiController` via a new
     `RoiEditPreviewChanged` event. This unblocks the existing UI buttons
     for ROI edit/submit/cancel.

---

## 11. What Cursor will NOT do without an explicit ticket

Per the AGENTS.md rules in this repo:

- No cross-package refactors not specified by a ticket.
- No moves between `acqstore` / `nicewidgets` / `cloudscope`.
- No GUI changes when the ticket is non-GUI.
- No silent behavior changes, no invented APIs, no backwards-compat scaffolding.
- Every ticket produces a report file under `docs/codex_tickets/`.
- All tests via `uv run pytest`.

If anything in this document looks wrong, the most useful next action is to
correct the specific item and re-run; the rest of the architecture description
is grounded in the existing source and the four reviewed docs.
