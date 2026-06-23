# Changelog

All notable changes to CloudScope will be documented in this file.

This project uses a simple changelog format inspired by Keep a Changelog. During development, add changes under `[Unreleased]`. When preparing a release, move those entries into a versioned section and leave a fresh empty `[Unreleased]` section at the top.

## [Unreleased]

### Added

### Changed

### Fixed

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
