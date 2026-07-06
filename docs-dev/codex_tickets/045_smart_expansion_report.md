# Ticket 045: SmartExpansion widget and Home page integration

## Files changed

- `src/nicewidgets/smart_expansion_widget/__init__.py` (new)
- `src/nicewidgets/smart_expansion_widget/smart_expansion.py` (new)
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/app_config.py`
- `src/cloudscope/views/app_config_view.py`
- `src/cloudscope/views/view_ids.py`
- `src/cloudscope/events/layout.py`
- `docs-dev/cloudscope_architecture.md`
- `tests/nicewidgets/test_smart_expansion.py` (new)
- `tests/cloudscope/test_smart_expansion_integration.py` (new)
- `tests/cloudscope/test_home_view_visibility_config.py` (removed)

## Summary of implementation

Added `SmartExpansion` in `nicewidgets/` as a CloudScope-agnostic wrapper around `ui.expansion`.
It fires `on_open` / `on_close` callbacks when the expansion opens or closes (user toggle or
programmatic `open()` / `close()`). `apply_initial_state()` dispatches the initial callback
after child content is built.

Integrated three `BaseView` panels on the Home page:

- `AcqImageListTreeView` (file list column)
- `AcqAnalysisPlotView` (analysis/reference splitter `before` pane)
- `ReferenceImageView` (analysis/reference splitter `after` pane)

Each view uses `initially_visible=False`; SmartExpansion wires `on_open=view.show` and
`on_close=view.hide` so MVC subscriptions and `refresh_from_state()` follow the existing
`BaseView` lifecycle.

Preserved the `ANALYSIS_REFERENCE` horizontal splitter between analysis plot and reference
image SmartExpansion panes (SplitterManager + AppConfig persistence unchanged).

Removed the `home_view_visible` AppConfig subsystem, `SetHomeViewVisibleIntent`, configurable
view registry, and AppConfigView visibility checkboxes. Panel show/hide is now user-controlled
via SmartExpansion headers.

No changes were required to the three wrapped view classes themselves.

## Tests added or modified

- `tests/nicewidgets/test_smart_expansion.py` — widget lifecycle unit tests
- `tests/cloudscope/test_smart_expansion_integration.py` — BaseView + SmartExpansion MVC wiring
- `tests/cloudscope/test_home_view_visibility_config.py` — removed (subsystem deleted)

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_smart_expansion.py tests/cloudscope/test_smart_expansion_integration.py -q
uv run pytest -q
```

## Test results

- Focused SmartExpansion tests: **11 passed**
- Full suite: **1049 passed**, 3 warnings (pre-existing)

## Concerns or follow-ups

- Expansion open/closed state is not persisted to AppConfig; all three panels default to open on
  each session.
- `ReferenceImageView.build()` still schedules one async load at build time even when the
  expansion starts closed; harmless but could be deferred in a future micro-fix.
- Disclosure triangle position should be verified visually in the running app; Quasar/CSS tweak
  can be added if needed.
