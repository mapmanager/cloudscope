# Changelog

All notable changes to CloudScope will be documented in this file.

This project uses a simple changelog format inspired by Keep a Changelog. During development, add changes under `[Unreleased]`. When preparing a release, move those entries into a versioned section and leave a fresh empty `[Unreleased]` section at the top.

## [Unreleased]

### acqstore (backend / data model)

### nicewidgets (reusable NiceGUI widgets)

### cloudscope (app / GUI)

### acqstore_server

### Desktop app

### Documentation

---

## [0.2.0] - YYYY-MM-DD

### acqstore (backend / data model)

Added:

- ND2 (Nikon) file loader wired into the loader factory, registry, and supported import extensions.
- OME-Zarr load and export (`ome_zarr_file_loader`, `acq_image.io.ome_zarr`) via bioio/zarr.
- TIFF export helpers and `AcqImage.save_as_tif` / `AcqImage.save_reference_as_tif`.
- Sum-intensity (ΔF/F₀) analysis module: core detection, event features, detection presets, and a synthetic data generator.
- Heart-rate analysis and velocity-event analysis as first-class dependent analyses computed from a parent `radon_velocity` analysis.
- Self-populating analysis registry with a `get_analysis_by_type` lookup.
- `AcqAnalysisSet.find_analysis(...)` lookup helper.
- Analysis pools for collection-level summaries: sum-intensity, velocity, and a shared base analysis pool.
- Randomized manifest / master-sampling API (`AcqImageManifest`) for blinded review workflows.
- Registered downloadable sample datasets `diameter-sample-data` and `velocity-sample-data` via `acqstore.sample_data.ensure_sample()` (same keys as the GUI sample-data menu items).
- Image-header physical-unit metadata loaded from a sidecar on file open.
- Analysis run metadata (`analysis_date`, `analysis_time`, `analysis_version`) stamped into velocity, diameter, heart-rate, and event summaries via `BaseAnalysis.finalize_summary()`.
- `DiameterAnalysis.summary_columns` schema for collection-level analysis pools.
- `AcqTrace` backend for electrophysiology-style traces, including an ABF (`.abf`) loader, sweep/epoch tables, sidecar JSON save, and trace peak-detection analysis.
- `dff0_diameter_analysis` common-analysis package for paired reporter + diameter coupling (continuous and triggered-event workflows).

Changed:

- OIR loader emits proper x/y axis labels; OIR and CZI folder-load performance improvements.
- OIR line-scan physical units from `seriesInterval` + pixel length; reference-image spatial scales from parent pixel length.
- CZI line-scan t→y dimension remap and reference-image dimension handling.
- Calibration / dimension-unit handling improvements for image headers and loaders.
- Structured load-error reporting (`LoadErrorType`) for missing files, unsupported types, loader errors, and CSV errors, including clearer failed-TIFF messages (e.g. Olympus 2-channel).
- Signal filtering can interpolate through small NaN gaps where applicable.

### nicewidgets (reusable NiceGUI widgets)

Added:

- New Plotly-based `plotly_plot` widget (context menu, display options, event overlay, models), replacing the ECharts analysis plot.
- Interactive velocity-event create/edit/delete in `plotly_plot` via selection handling.
- Interactive Set F₀ / baseline editing support in Plotly plots (hline drag, constrained drag, percentile toolbar helpers).
- Reusable `ContrastWidget` (LUT select, Auto, and min/max range) embedded in the image toolbar.
- `UploadWidget` for browser file upload.
- Interactive ROI editing in the raster viewer (create / move / resize ROI overlays).
- `tree_widget` promoted into nicewidgets with an index column.
- NicePool plot presets (save/load/delete), pool control panel, selection handler, preset validation, and table metadata display.
- Compact select styles and compact image-toolbar UI.
- `plotly_axis_layout` / `plotly_layout_margins` helpers for aligned x-axes across stacked plots.
- `NicePool.relayout_plots()` for plot refresh after embedded resize.

Changed:

- Raster viewer migrated to Plotly: relayout-based zoom/pan, trace and ROI overlays, margin alignment with `plotly_plot`.
- NicePool single-scrollbar toolbar layout; embedded `h-full` / `min-h-0` sizing instead of `h-screen`.

Fixed:

- Plotly user-set x-range infinite-loop (echo) fix.
- ROI rectangle edit flashing/padding in the raster viewer.
- File-tree selection / scroll-into-view reliability (initial selection, programmatic vs user click, reduced selection flash).

### cloudscope (app / GUI)

Added:

- Sum-intensity analysis view, parameters view, plot view, and pool integration.
- Interactive Set F₀ mode in the sum-intensity plot (live baseline edit, dual-plot / toolbar controls).
- Right-side velocity pool panel on the home page: collapsible splitter, persisted open width, header toggle, and lazy build.
- Primary-image t/z slicing sliders with viewport preservation while scrubbing.
- Blinded display mode.
- App Info log viewer (Open Logs button + in-app log preview) backed by a unified `cloudscope.log`.
- Live build-info rows in App Info (version / build metadata when packaged or deployed).
- Batch-analysis dialog with ROI-mode selection, preview rows, live per-file results, progress, and cancellation.
- Split experiment-metadata and image-header metadata into distinct views with a dedicated left-toolbar button.
- Reference-image metadata display and **Save Reference As Tif** (native dialog + browser download).
- `analysis_summary_display` helpers for formatted velocity/diameter summary expansions.
- Factory reset in runtime and the options view.
- Reference-image scan-path traces; reference image relocated to the left toolbar.
- x-range controller, sum-intensity pool controller, and velocity pool controller.
- `VelocityPoolView.relayout_plots()`, `SplitterManager` right-pool helpers, and `RIGHT_POOL` splitter preset.

Changed:

- Home page layout refactor for natural scrolling and right-toolbar pool integration.
- Velocity and diameter analysis views show a collapsed summary expansion instead of a raw dict; summary floats rounded to three decimals.
- Velocity pool column naming no longer double-prefixed (`velocity_velocity_mean` → `velocity_mean`).
- App-config table font and dark-mode UI polish.
- File tree auto-fits to splitter height; load file/folder buttons disabled in web-server mode.
- Disconnect/reconnect session restore and page-layout chrome restore improvements.

Fixed:

- Reference image view when no reference image is present (clear on missing).
- Diameter analysis int→float mapping bug.
- Reference plot physical-axis display when calibration metadata is present.

### acqstore_server

Added:

- New `acqstore_server` package: HTTP API over acqstore loaders (API-only uvicorn and optional native status UI).
- Session pick/open lifecycle, reference/overview payloads, and demo HTML clients (v1 and v2).
- v2 API surface: capabilities, session lifecycle, OpenAPI discoverability, stable error envelopes, and header contract.
- Gzip-friendly session fetch path for large payloads.
- Manual-dispatch macOS packaging workflow for AcqStore Server (separate from CloudScope desktop releases).

### Desktop app

Added:

- Option C desktop quit flow with a native Save / Don't Save / Cancel dialog and synchronous dirty-file save on quit.
- Native window menu title.
- Desktop app icons (CS) for macOS and Windows packaging.

Changed:

- Desktop launcher defaults back to single-window mode; the velocity pool is embedded in the home page instead of a separate native window.
- `WindowGeometryTracker` syncs live geometry on window close before persisting config.
- Windows / macOS build scripts and CI path fixes; build-info embedded in packaged artifacts.

Fixed:

- Option C window geometry could be lost when closing because persistence ran after the pywebview window was destroyed.
- Embedded velocity pool plots could fail to relayout after the right-panel splitter was resized.

### Documentation

- Major MkDocs restructure with expanded end-user recipes (velocity, diameter, sum-intensity, velocity-event, heart-rate).
- New notebooks: sum intensity, heart rate, heart-rate batch, kymograph reference image, and generating a randomized file subset for unbiased analysis.
- New blinded-mode and supported-file-formats end-user pages; a heart-rate data-scientist page; and heart-rate, event-analysis, and analysis-pool API pages.
- MkDocs notebooks transition from the retired `demo-small` sample to the registered `diameter-sample-data` and `velocity-sample-data` datasets.
- New install-desktop-app guide (form-based desktop distribution) and desktop-app request form; empty-`__init__` and no-README-driveby contributor policies.
- Google Analytics on the MkDocs site (and web-server HTML injection for the hosted app).

---

## [0.1.3] - 2026-06-23

### Added

- Two-window desktop mode: home page + plot pool in separate native windows.
- Desktop launcher with pywebview, window geometry persistence, and theme sync.
- Lazy TIFF loading in acqstore file loaders.
- CZI reference image support and dimension handling improvements.
- Load controller integration with task runner for file-tree loads.
- LRU cache for image pyramid builds; raster display cache in cloudscope.
- SmartExpansion in nicewidgets: when expansion is closed, child BaseView(s) disconnect from MVC for responsiveness; when open, they reconnect and refresh from current app state.
- SmartExpansion on home page for file list, analysis plot, and reference image panels.

### Changed

- Refactored native windowing away from NiceGUI main_window to pywebview.
- Updated home page splitter to use SmartExpansion.
- Raster viewer: relayout-based zoom/pan, pyramid level constraints, kymograph fixes.
- acqstore scan-path / reference-image API updates.

### Fixed

- macOS PyInstaller multiprocessing freeze (multiple window relaunch).
- Plotly mouse+wheel zoom and heatmap corruption with space dim 1.
- macOS two-finger context menu in Plotly raster view.
- Reference image view when no reference image is present.

### Documentation

- Added kymograph reference-image MkDocs notebook.
- Expanded velocity, diameter, and heart rate notebooks.

---

## [0.1.0] - 2026-06-10

### Added

- Added first official GitHub Release workflow for reproducible CloudScope releases.
- Added local release metadata checks for tag, version, and changelog consistency.
- Added docs and source archive artifacts to GitHub Releases.

### Changed

- Improved GitHub Actions run names for easier reading in the Actions UI.

## [0.1.1] - 2026-06-11

### Added

- Implemented MkDocs documentation site using Material for MkDocs and mkdocstrings.

- Added expanded documentation structure for end users, scientific users, and developers.

- Added GitHub Actions workflows for building Windows and macOS desktop application artifacts.

- Added signed, notarized, and stapled macOS Apple Silicon application build workflow.

- Added unsigned Windows desktop application build workflow using NiceGUI Pack and PyInstaller.

### Changed

- Added new ECharts context menu items.

- Improved CI/CD release process for reproducible tagged CloudScope releases.

- Improved desktop build artifact naming and packaging conventions.

### Fixed

- Fixed release notes extraction for GitHub Release generation.

## [0.1.2] - 2026-06-11

### Fixed

- Fixed macOS build metadata generation when building from a git tag.

- Fixed the automated macOS release asset build path for tagged releases.
