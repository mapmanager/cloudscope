# 037 — Toolbar select width, embedded events visibility, Plotly legend position

## Summary

Three independent GUI/UX fixes:

1. **Image toolbar channel/ROI select labels clipped.** The `Channel` and `ROI`
   `ui.select` controls in `ImageToolbarWidget` had no width, so their outlined
   floating labels were truncated. Added a `min-w-28` class to both selects so
   the labels render fully.

2. **Embedded `EventAnalysisView` invisible inside `VelocityAnalysisView`.** Root
   cause (confirmed in browser): Quasar `q-card` defaults to `flex-wrap: wrap`.
   The velocity panel card has a fixed height (`h-full`) and stacks many children
   in a flex column. When content exceeds the panel height, items after the run
   button (batch button and embedded event view) wrapped into a **second flex
   column starting at the top**, overlapping the velocity controls instead of
   stacking below them. The event view was built and visible in the DOM but not
   shown in the expected vertical position. Fix: add `flex-nowrap` to the
   velocity card classes so all children stack in one column and scroll via
   `overflow-y-auto`. Also keep embedded event view as always-visible nested
   content with a fixed table height for AG Grid.

3. **Plotly legend moved from right to bottom.** Added a horizontal,
   bottom-anchored `legend` block to the base figure layout in
   `build_plotly_figure`. No legend display logic changed; the setting is
   harmless when no legend is shown and applies once trace overlays add a
   legend.

## Files changed

- `src/nicewidgets/image_toolbar_widget/image_toolbar_widget.py` — `min-w-28` on
  channel and ROI selects.
- `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py` — horizontal
  bottom legend in `build_plotly_figure` layout.
- `src/cloudscope/views/event_analysis_view.py` — optional `table_height_px`
  param; embedded non-shrinking root/table-height handling.
- `src/cloudscope/views/velocity_analysis_view.py` — `_EMBEDDED_EVENT_TABLE_HEIGHT_PX`
  constant; pass fixed table height to the embedded event view and build it as
  visible embedded content; `flex-nowrap` on the velocity card.
- `src/nicewidgets/table_widget/table_widget.py` — suppress AG Grid Enterprise
  right-click menu globally (`suppressContextMenu` + `preventDefaultOnContextMenu`)
  so only the widget's own `ui.context_menu` shows, matching `TreeWidget`.

## Tests added or modified

- `tests/cloudscope/test_event_analysis_view.py` — added
  `test_table_height_px_defaults_to_none` and
  `test_table_height_px_is_stored_when_provided`.
- `tests/cloudscope/test_velocity_analysis_view.py` — added
  `test_velocity_analysis_view_embeds_event_view_with_fixed_table_height`; updated
  ownership expectation for visible embedded content.
- `tests/nicewidgets/test_table_widget_smoke.py` — added
  `test_build_aggrid_options_suppresses_enterprise_context_menu`.

## Test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_analysis_view.py tests/cloudscope/test_event_analysis_view.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_protocol.py -q
uv run pytest src/nicewidgets/raster_viewer/tests/frontend/test_plotly_protocol.py src/nicewidgets/image_toolbar_widget -q
uv run pytest tests/cloudscope/test_left_toolbar_view.py tests/cloudscope/test_velocity_analysis_view.py tests/cloudscope/test_event_analysis_view.py -q
uv run pytest tests/nicewidgets/test_table_widget_smoke.py tests/nicewidgets/test_table_widget_context_menu.py tests/cloudscope/test_event_analysis_view.py -q
```

## Test results

- 48 passed (view + plotly protocol tests).
- 7 passed (plotly protocol + toolbar widget collection).
- 42 passed (left toolbar + velocity/event view tests).
- 62 passed (table widget smoke/context-menu + event view tests).

## Concerns / follow-ups

- `min-w-28` (7rem) was chosen as the smallest width that reliably shows the
  `Channel` label; adjust if the toolbar is themed with a larger font.
- The embedded event table height (`300px`) is a fixed default; can be exposed
  via `AppConfig` later if a configurable height is desired.
- Pre-existing Ruff warning in `event_analysis_view.py` (`getattr` with constant
  attribute) was left untouched as it is unrelated to this ticket.
