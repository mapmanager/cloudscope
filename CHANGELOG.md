# Changelog

All notable changes to CloudScope will be documented in this file.

This project uses a simple changelog format inspired by Keep a Changelog. During development, add changes under `[Unreleased]`. When preparing a release, move those entries into a versioned section and leave a fresh empty `[Unreleased]` section at the top.

## [Unreleased]

### Added

### Changed

### Fixed

### Documentation

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