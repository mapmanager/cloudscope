# Changelog

All notable changes to CloudScope will be documented in this file.

This project uses a simple changelog format inspired by Keep a Changelog. During development, add changes under `[Unreleased]`. When preparing a release, move those entries into a versioned section and leave a fresh empty `[Unreleased]` section at the top.

## [Unreleased]

### Added

- Analysis run metadata (`analysis_date`, `analysis_time`, `analysis_version`) stamped into velocity, diameter, heart-rate, and event summaries via `BaseAnalysis.finalize_summary()`.
- `DiameterAnalysis.summary_columns` schema for collection-level analysis pools.
- Right-side velocity pool panel on the home page with collapsible splitter, persisted open width, and header toggle button.
- `analysis_summary_display` helpers for formatted velocity/diameter result summary expansions.
- Option C desktop quit flow with native Save / Don't Save / Cancel dialog and synchronous dirty-file save on quit.
- `NicePool.relayout_plots()` and `VelocityPoolView.relayout_plots()` for plot refresh after embedded pool resize.
- `SplitterManager` right-pool open/collapse helpers and `RIGHT_POOL` splitter preset.

### Changed

- Desktop launcher defaults back to single-window mode; velocity pool is embedded in the home page right panel instead of requiring a separate native window.
- Home page layout refactor for natural scrolling and right-toolbar velocity pool integration.
- Velocity and diameter analysis views show a collapsed summary expansion instead of a raw summary dict label.
- Velocity analysis pool column naming: metric keys such as `velocity_mean` are no longer double-prefixed (`velocity_velocity_mean`).
- Analysis summary display rounds float values to three decimal places.
- `WindowGeometryTracker` syncs live geometry on window close before persisting config to disk.
- NicePool embedded layout uses `h-full` / `min-h-0` sizing instead of `h-screen` for splitter panes.

### Fixed

- Option C desktop window geometry could be lost when closing because persistence ran after the pywebview window was destroyed.
- Embedded velocity pool plots could fail to relayout correctly after the right-panel splitter was resized.

### Documentation

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
