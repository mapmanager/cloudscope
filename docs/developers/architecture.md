# Architecture

CloudScope is organized around separation of concerns.

- `acqstore`: backend acquisition objects, metadata, ROIs, file loaders, analysis, sample data, and result persistence.
- `nicewidgets`: reusable NiceGUI widgets that are not CloudScope-specific.
- `cloudscope`: application state, controllers, views, dialogs, and user-facing workflows.

The GUI should remain thin. Scientific logic belongs in `acqstore`; reusable UI logic belongs in `nicewidgets`; application orchestration belongs in `cloudscope`.
