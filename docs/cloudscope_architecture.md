# CloudScope Architecture

## Purpose

CloudScope is a thin NiceGUI application for viewing, annotating, and analyzing acquisition-backed files. It is not the domain model. It is not the widget library. Its primary job is to compose application views, route user intent through controllers, and display state from backend APIs.

The core architectural rule is:

```text
CloudScope stays thin.
acqstore owns acquisition/image/ROI/analysis interpretation.
nicewidgets owns reusable GUI widgets.
CloudScope orchestrates them.
```

If CloudScope code starts interpreting image layout, reference-image channels, analysis table columns, ROI coordinate systems, or file-format-specific metadata, that logic probably belongs in acqstore. If CloudScope code starts containing reusable widget internals, that logic probably belongs in nicewidgets.

## Package roles

### acqstore

acqstore is the domain/data API used by CloudScope and any future GUI, script, notebook, or service. It should provide public APIs that are sufficient for a thin viewer.

Responsibilities:

```text
- AcqImage and AcqImageList domain model
- image and reference-image access
- metadata schemas and values
- ROI model and ROI persistence
- analysis model, analysis persistence, and analysis result APIs
- long-running analysis APIs with progress/cancel hooks
- load/save APIs with progress/cancel hooks
- GUI-facing data helpers such as ReferenceImage.get_plane() and analysis.get_plot_data()
```

### nicewidgets

nicewidgets is the reusable widget layer. It should not know CloudScope-specific state or controllers.

Responsibilities:

```text
- PlotlyRasterViewer
- ROI overlay rendering/edit primitives
- EChartWidget
- image toolbar widget
- metadata widgets if reusable
- widget-local intent/event models
- efficient browser-side updates such as Plotly.relayout where appropriate
```

### cloudscope

CloudScope is the application layer.

Responsibilities:

```text
- NiceGUI app entry point
- page composition
- application state
- event bus
- controllers
- task runner wiring
- view lifecycle
- app configuration
- packaging/runtime config
```

CloudScope should call acqstore and nicewidgets APIs rather than duplicate their logic.

## Source tree overview

Typical tree:

```text
src/cloudscope/
├── app.py
├── app_config.py
├── build_info.py
├── events.py
├── event_bus.py
├── state.py
├── pages/
│   └── home_page.py
├── controllers/
│   ├── home_page_controller.py
│   ├── load_save_controller.py
│   ├── analysis_controller.py
│   └── roi_controller.py
└── views/
    ├── base_view.py
    ├── view_manager.py
    ├── left_toolbar_view.py
    ├── app_config_view.py
    ├── app_info_view.py
    ├── file_list_view.py
    ├── image_toolbar_view.py
    ├── primary_image_view.py
    ├── reference_image_view.py
    ├── acq_analysis_plot_view.py
    ├── task_progress_dialog_view.py
    ├── splitter_manager.py
    └── splitter_handle.py
```

## Runtime startup flow

High-level flow:

```text
src/cloudscope/app.py
  -> reads environment/runtime configuration
  -> configures native/window behavior when appropriate
  -> registers NiceGUI page routes
  -> ui.run(...)

@ui.page('/') home_page()
  -> creates per-client EventBus, AppState, AppConfig, controllers, ViewManager
  -> constructs HomePage
  -> HomePage.build()
```

The page and view objects are per-client. Do not put per-client mutable UI state in module globals.

## HomePage composition

`HomePage` is the main page composer. It should create the high-level layout regions and wire controllers/views together. It should not contain domain logic and should not implement widget internals.

Current responsibilities:

```text
- instantiate controllers
- instantiate ViewManager
- create the left toolbar and main page views
- create splitters and register them with SplitterManager
- wire ResetHomeLayoutIntent and home-view visibility intents
- register views with ViewManager
```

HomePage should stay as a composition layer. If layout logic grows, move it into helpers such as `SplitterManager`. If a workflow grows, move it into a controller.

## Event architecture

CloudScope uses an application event bus. Events fall into categories. Keep these categories clear; mixing them is the main source of event-system confusion.

### Intent events

Intent events mean: a user or view requested something. Controllers consume intent events. Intent events do not mean state has already changed.

Examples:

```text
SelectFileIntent
SelectChannelIntent
SelectRoiIntent
AddRoiIntent
DeleteRoiIntent
BeginEditRoiIntent
SubmitEditRoiIntent
CancelEditRoiIntent
RunAnalysisIntent
CancelTaskIntent
LoadPathIntent
SaveSelectedIntent
SaveAllIntent
SetHomeViewVisibleIntent
ResetHomeLayoutIntent
```

Rule:

```text
Views emit intent events.
Controllers handle intent events.
```

### Selection state events

Selection state events mean the canonical app selection has changed.

Examples:

```text
FileSelectionChanged
ChannelSelectionChanged
RoiSelectionChanged
```

Most views should not subscribe to these directly. `BaseView` subscribes to them and calls `on_primary_selection_changed()`.

### Model-change state events

Model-change events mean a backend object changed while the selection may or may not have changed.

Examples:

```text
FileListChanged
MetadataChanged
AnalysisCompleted
RoiChanged
```

Subscribe to these only when a view must refresh because the selected object changed internally without a selection change.

Examples:

```text
FileListView consumes MetadataChanged, AnalysisCompleted, RoiChanged to update rows.
ImageToolbarView consumes RoiChanged because its ROI option list may change.
PrimaryImageView consumes RoiChanged because ROI overlays may change.
AcqAnalysisPlotView consumes AnalysisCompleted because plot data may appear without selection changing.
```

Avoid speculative subscriptions. If selection changes already refresh a view, use the selection path.

### Task/progress events

Examples:

```text
AppBusyChanged
TaskProgressChanged
AppStatusChanged
```

These coordinate long-running workflows and UI blocking.

### Layout/config events

Examples:

```text
SetHomeViewVisibleIntent
ResetHomeLayoutIntent
```

These mutate view/layout state and in-memory AppConfig. They should not perform hidden saves.

## Controllers

Controllers are workflow owners. They consume intent events, mutate app state or backend objects, and publish state events.

### HomePageController

Owns canonical `AppState` and selection changes.

Responsibilities:

```text
- select file
- select channel
- select ROI
- update AppState
- publish FileSelectionChanged / ChannelSelectionChanged / RoiSelectionChanged
- load demo/current lists when invoked by other controllers
```

Public selection methods are useful so other controllers do not mutate `AppState` directly.

### LoadSaveController

Owns load/save workflows.

Responsibilities:

```text
- handle load/save intents
- call acqstore AcqImageList load/save APIs
- use TaskRunner for cancellable long-running load/save work
- publish FileListChanged and status/progress events
```

Load/save is not a UI concern. Views should emit load/save intents only.

### AnalysisController

Owns analysis execution.

Responsibilities:

```text
- handle RunAnalysisIntent
- snapshot current selection
- run acqstore analysis through TaskRunner
- pass progress/cancel callbacks into acqstore analysis APIs
- publish AnalysisCompleted
```

AnalysisController does not save files. Saving remains explicit.

### RoiController

Owns ROI CRUD workflows.

Responsibilities:

```text
- handle AddRoiIntent / DeleteRoiIntent / edit intents
- mutate acq_image.rois
- remove dependent analysis through acq_image.analysis_set when ROI geometry/lifecycle invalidates it
- select new/remaining ROI via HomePageController
- publish RoiChanged
```

For ordinary ROI selection, use `SelectRoiIntent` and `RoiSelectionChanged`. `RoiChanged` is for ROI model changes, not selection.

## BaseView API

`BaseView` is the shared lifecycle and state helper for views.

### Lifecycle

Expected methods:

```text
build()
show()
hide()
on_show()
on_hide()
subscribe_events()
refresh_from_state()
on_primary_selection_changed()
```

`build()` creates UI elements. `show()`/`hide()` manage visibility and subscriptions. `on_show()` subscribes common events and refreshes the view. `on_hide()` removes subscriptions.

### Automatic subscriptions

`BaseView.on_show()` subscribes to:

```text
AppBusyChanged
FileSelectionChanged
ChannelSelectionChanged
RoiSelectionChanged
```

Derived views should not normally subscribe to these manually. Override `on_primary_selection_changed()` instead.

### Selection state

BaseView maintains:

```text
current_selection
current_acq_image
```

Selection-dependent views should use BaseView helpers rather than duplicating state.

Typical helpers:

```text
get_acq_image_list()
get_acq_image_by_file_id(file_id)
get_selected_acq_image()
has_valid_primary_selection()
selected_acq_image_is_dirty()
```

Rule:

```text
Events tell a view to refresh.
BaseView/AppState provide current truth.
Views should not maintain duplicate backend state unless they need a temporary async snapshot.
```

Legitimate temporary snapshot example:

```text
PrimaryImageView may snapshot file/channel/image before async raster loading.
```

Illegitimate duplicated state example:

```text
A view caching selected dirty state when it can call selected_acq_image_is_dirty().
```

### Busy behavior

BaseView supports:

```text
disable_when_busy
```

During `AppBusyChanged(True)`, most views are disabled, not hidden. Task UI remains available. Cancel paths must stay reachable.

### Custom events in derived views

Derived views should subscribe only to events that represent data changing without selection changing.

Examples:

```text
AcqAnalysisPlotView: AnalysisCompleted
FileListView: FileListChanged, MetadataChanged, AnalysisCompleted, RoiChanged
ImageToolbarView: RoiChanged, RoiEditModeChanged
PrimaryImageView: RoiChanged
```

Do not subscribe to `RoiChanged` just because the current ROI changed. Use `RoiSelectionChanged` through BaseView for that.

## ViewManager

`ViewManager` tracks view instances by `ViewId` and centralizes show/hide operations.

Responsibilities:

```text
- register views
- show/hide one view
- set visibility programmatically
- optionally show only one view among a candidate group
```

Use it for runtime visibility changes such as AppConfig-controlled main-page view visibility. Avoid having views directly manipulate sibling views.

## Home page layout and splitters

HomePage uses nested splitters to control layout:

```text
LEFT_TOOLBAR
  before: LeftToolbarView
  after: main content

FILE_LIST
  before: LoadSaveView + AcqImageListTableView
  after: primary/analysis/reference area

PRIMARY_IMAGE
  before: ImageToolbarView + PrimaryImageView
  after: analysis/reference area

ANALYSIS_REFERENCE
  before: AcqAnalysisPlotView
  after: ReferenceImageView
```

`SplitterManager` owns programmatic splitter values and reset behavior.

AppConfig stores splitter values in memory and saves/reloads through the app config JSON lifecycle. No hidden save should happen merely because a user drags a splitter.

`ResetHomeLayoutIntent` resets splitters to factory defaults and closes the left toolbar panel.

## Configurable view visibility

AppConfig stores main-page view visibility as a dictionary:

```text
home_view_visible: dict[str, bool]
```

Configurable views are declared centrally in `views/view_ids.py`, for example:

```text
AcqImageListTableView
AcqAnalysisPlotView
ReferenceImageView
```

AppConfigView builds checkboxes from that registry. Checkbox changes emit an intent. HomePage applies visibility through ViewManager and updates AppConfig in memory.

Unknown visibility keys loaded from JSON should be ignored. Missing known keys should use defaults. This allows adding/removing configurable views without a config version bump.

## Long-running tasks

CloudScope has multiple long-running workflows. They should share the same TaskRunner infrastructure.

### One active task rule

Only one long-running task is active at a time. This avoids conflicting state changes and simplifies cancellation semantics.

### Analysis tasks

Flow:

```text
VelocityAnalysisView / Analysis UI
  -> RunAnalysisIntent
  -> AnalysisController
  -> TaskRunner
  -> acqstore analysis API with progress/cancel callbacks
  -> TaskProgressChanged events
  -> AnalysisCompleted
```

Analysis completion mutates the selected AcqImage in memory and marks it dirty. Saving remains explicit.

### Load/save tasks

Flow:

```text
LoadSaveView
  -> load/save intent
  -> LoadSaveController
  -> TaskRunner
  -> acqstore AcqImageList load/save API with progress/cancel callbacks
  -> FileListChanged / status events
```

Load cancel should not replace the current app list unless load completes successfully. Save cancel preserves files already saved and skips files not yet reached.

### Blocking signal

`TaskRunner` publishes:

```text
AppBusyChanged(True)
```

Effects:

```text
- disables most BaseView-derived UI
- prevents conflicting user actions
- does not hide views
- keeps task progress dialog/cancel available
```

Terminal task events should publish terminal progress/status before:

```text
AppBusyChanged(False)
```

This allows progress/status views to display completion/cancel/failure before UI re-enables.

## ROI CRUD architecture

### Add ROI

```text
ImageToolbarView
  -> AddRoiIntent
  -> RoiController
  -> acq_image.rois.create_rect_roi()
  -> HomePageController.select_roi(new_roi_id)
  -> RoiSelectionChanged
  -> RoiChanged(ADD)
```

Most views refresh from `RoiSelectionChanged`. Only views needing option/overlay/row updates consume `RoiChanged`.

### Delete ROI

```text
ImageToolbarView
  -> DeleteRoiIntent
  -> RoiController
  -> if dependent analysis exists, ask confirmation
  -> acq_image.analysis_set.delete_roi(roi_id)
  -> acq_image.rois.delete(roi_id)
  -> select remaining ROI or None
  -> RoiSelectionChanged
  -> RoiChanged(DELETE)
```

Deleting an ROI deletes analysis for that ROI across all channels, because ROIs are not channel-specific.

### Edit ROI

Edit mode is staged:

```text
BeginEditRoiIntent
RoiEditModeChanged(active=True)
RoiEditPreviewChanged(bounds)
SubmitEditRoiIntent
CancelEditRoiIntent
RoiChanged(EDIT)
```

Geometry editing should use nicewidgets Plotly ROI overlay APIs. CloudScope should not directly parse Plotly internals beyond widget public APIs.

## Analysis architecture

acqstore owns analysis implementations and analysis result APIs. CloudScope should not know analysis table column names.

Analysis plot flow:

```text
selected AcqImage/channel/roi
  -> analysis_set lookup
  -> analysis.get_plot_data()
  -> AcqAnalysisPlotView
  -> EChartWidget.set_line_data(...)
```

For radon velocity, acqstore provides:

```text
x = time_s
y = velocity
x_label = Time (s)
y_label = Velocity
```

CloudScope should treat this as opaque plot data.

## Image viewers

### PrimaryImageView

Displays the primary acquisition image via nicewidgets PlotlyRasterViewer. It also owns current ROI overlays for display/edit workflows.

Responsibilities:

```text
- load selected image plane from acqstore API
- pass raster data to PlotlyRasterViewer
- build ROI overlays from acqstore ROI API
- select/highlight current ROI
- respond to RoiChanged for overlay list refresh
```

Avoid image interpretation logic in PrimaryImageView. If the view needs a special image plane, acqstore should expose a GUI-ready API.

### ReferenceImageView

Displays reference images when available. It should call acqstore `ReferenceImage.get_plane(channel)` or equivalent. It should not interpret reference-image dimensionality, scaling, coordinate arrays, or line ROIs itself.

Future line segment display should consume a clean acqstore API for a display-ready line segment.

## AppConfig architecture

AppConfig stores user/application runtime preferences. It saves/loads JSON.

Examples:

```text
recent paths
splitter values
main-page view visibility
font sizes
```

Rules:

```text
- no hidden save for important user data
- app config may be saved on explicit user action or app quit
- unknown JSON keys should not break load
- missing keys should receive defaults
```

## Testing strategy

Prefer unit tests around:

```text
- event/controller behavior
- BaseView helpers
- view methods with fake widgets
- AppConfig save/load behavior
- acqstore public APIs
- nicewidgets model/options generation
```

Avoid brittle tests that depend on actual browser rendering. Use fake widgets and direct method calls for most view logic.

For NiceGUI-specific behavior, test as close to the boundary as possible and keep tests minimal.

## Stress points and improvement areas

### events.py is large

The current single `events.py` is workable but increasingly broad. Consider splitting later:

```text
cloudscope/events/
  __init__.py
  base.py
  selection.py
  roi.py
  analysis.py
  task.py
  load_save.py
  layout.py
  metadata.py
```

Use `events/__init__.py` to re-export names so existing imports remain stable during migration.

### View subscriptions can drift

Views can accidentally subscribe to model-change events they do not need. Rule of thumb:

```text
Selection change -> BaseView.on_primary_selection_changed()
Model changed without selection change -> custom subscription
```

Review subscriptions periodically.

### HomePage can grow too large

HomePage should remain a composer. If logic grows, move it into:

```text
SplitterManager
ViewManager
controllers
view-specific classes
```

### acqstore APIs must keep expanding

Whenever CloudScope needs to interpret backend structures, prefer adding/cleaning an acqstore API. This is especially important for:

```text
reference image planes
analysis plot data
ROI dependency reports
load/save progress/cancel
analysis progress/cancel
```

### nicewidgets APIs must stay clean

Do not let CloudScope manipulate widget internals. Add public widget APIs for:

```text
ROI overlays
axis range linking
plot data update
edit preview state
```

### Layout CSS is fragile

NiceGUI + nested splitters + Plotly/ECharts require careful `h-full`, `flex-1`, `min-h-0`, and `overflow-hidden` usage. Layout should be tested manually after splitter/view changes.

### Long task cancellation is cooperative

Cancellation depends on backend APIs checking cancellation callbacks. Any new long task must be designed with cancellation checkpoints.
