# Ticket 029 - nicewidgets contrast widget

Reusable `ContrastWidget` (LUT select, Auto button, min/max range) added to
`nicewidgets/`, backed by a per-channel `ImageContrast` on each `AcqImage`,
wired through a new `ContrastController` + event family, and embedded inside
`ImageToolbarView` on the existing row. `PrimaryImageView` is now the single
decoder of 2D slice data and publishes `PrimaryPlaneLoaded` so the toolbar can
seed contrast without re-decoding.

## Files changed

### New source files

- `src/nicewidgets/contrast_widget/__init__.py`
- `src/nicewidgets/contrast_widget/colorscales.py` - `COLORSCALE_OPTIONS`,
  `colorscale_option_values`, and `get_colorscale` (ported and trimmed from
  kymflow).
- `src/nicewidgets/contrast_widget/intent.py` - single frozen
  `ContrastChangedIntent(color_lut, value_min, value_max)`.
- `src/nicewidgets/contrast_widget/contrast_widget.py` - `ContrastWidget(ui.row)`
  with injected `auto_contrast_callback`, `*_ext` setters, exception-safe
  Auto handler, and single-emit guarantee.
- `src/acqstore/acq_image/image_contrast.py` - `ImageContrast` dataclass and
  `contrast_clip_min_max(img, *, percentile_low, percentile_high)`.
- `src/cloudscope/events/contrast.py` - `UpdateImageContrastIntent`,
  `ImageContrastChanged`.
- `src/cloudscope/events/raster.py` - `PrimaryPlaneLoaded` (read-only plane
  reference).
- `src/cloudscope/controllers/contrast_controller.py` - dumb controller that
  never decodes slices.

### Modified source files

- `src/acqstore/acq_image/acq_image.py`
  - Added per-channel `_image_contrasts` dict, `_image_contrast_dirty` flag,
    and public API: `get_image_contrast`, `set_image_contrast`,
    `ensure_image_contrast_from_plane`.
  - Sidecar persistence (no version bump; `image_contrast` added as an
    *optional* key) inside `# region image_contrast persistence` markers in
    `_build_sidecar_payload` and `_apply_loaded_sidecar_payload`. Removing
    these blocks fully disables persistence with no other code changes.
  - New module constant `_ACQIMAGE_SIDECAR_OPTIONAL_KEYS = {'image_contrast'}`
    so the unknown-keys check stays silent.
  - `is_dirty` defensively uses `getattr` for `_image_contrast_dirty` to
    remain compatible with tests that build `AcqImage.__new__`.
- `src/cloudscope/app_config.py`
  - `AppConfigData` gains `contrast_auto_percentile_low`,
    `contrast_auto_percentile_high`, and `default_channel_color_lut: dict`.
  - Parsing tolerates malformed JSON values; percentiles are clamped to
    `[0, 100]` and swapped when inverted.
  - Public accessors: `get_contrast_auto_percentiles`,
    `set_contrast_auto_percentiles`, `get_default_channel_color_lut`,
    `set_default_channel_color_lut`.
- `src/cloudscope/pages/home_page.py`
  - Instantiates and binds `ContrastController`.
  - Passes `app_config` into `ImageToolbarView`.
- `src/cloudscope/views/image_toolbar_view.py`
  - Adds `ContrastWidget` next to `ImageToolbarWidget` on the same `ui.row`.
  - Subscribes to `PrimaryPlaneLoaded` and `ImageContrastChanged`.
  - Disables the contrast widget on every `(file_id, channel)` transition
    and re-enables it from `_on_plane_loaded` after seeding the widget.
  - `_compute_auto_contrast` reads percentiles from `AppConfig`.
- `src/cloudscope/views/primary_image_view.py`
  - `_load_plane_payload` now returns `(plane, grid, is_placeholder)`.
  - After a real plane is set on the viewer, calls `plane.setflags(write=False)`
    and publishes `PrimaryPlaneLoaded`.
  - Subscribes to `ImageContrastChanged` and applies LUT + window via
    `PlotlyRasterViewer.set_heatmap_colorscale` and `set_heatmap_contrast`
    after `set_data` and on contrast events.

### New tests

- `tests/nicewidgets/test_contrast_widget.py` (12 cases) - construct,
  `*_ext` no-emit, user handlers, Auto with/without callback, Auto swap,
  Auto exception handling.
- `tests/acqstore/test_image_contrast.py` (12 cases) - clip helper for
  uint8/uint16/float, clamping, swap, idempotent seeding, dirty-marking
  asymmetry, loader instrumentation contract.
- `tests/cloudscope/test_app_config_contrast.py` (11 cases).
- `tests/cloudscope/test_contrast_controller.py` (5 cases) - happy path,
  unknown file, missing prior contrast, no slice decode.

### Extended tests

- `tests/acqstore/test_acq_image_sidecar.py` - top-level contract updated
  to include `image_contrast`; new tests round-trip single + many channels,
  load with the key absent, tolerate malformed entries, and assert no
  unknown-key warning.
- `tests/cloudscope/test_image_toolbar_view.py` - intent forwarding,
  selection-change disable, plane-loaded seeding, contrast-changed echo,
  AppConfig percentile wiring.
- `tests/cloudscope/test_primary_image_view.py` - signature change for
  `_load_plane_payload`, contrast apply path, no publish for placeholder.

## Tests run

```bash
uv run pytest tests/nicewidgets/test_contrast_widget.py
uv run pytest tests/acqstore/test_image_contrast.py tests/acqstore/test_acq_image_sidecar.py
uv run pytest tests/cloudscope/test_app_config_contrast.py
uv run pytest tests/cloudscope/test_contrast_controller.py
uv run pytest tests/cloudscope/test_primary_image_view.py
uv run pytest tests/cloudscope/test_image_toolbar_view.py
uv run pytest
```

## Test results

- Full suite: **896 passed**, 3 pre-existing warnings, no failures.
- Focused suites (counts above) all pass.

## Implementation contract notes

- **One decode per selection.** `AcqImage.image_contrast` paths never call
  `get_slice_data`; `ContrastController` never calls it. Both contracts are
  asserted by loader-instrumented tests.
- **Dirty-marking asymmetry.** `ensure_image_contrast_from_plane` does not
  mark `is_dirty`; `set_image_contrast` does. Both are pinned by tests.
- **`PrimaryPlaneLoaded.plane` is read-only.** `PrimaryImageView` calls
  `setflags(write=False)` before publish; the event docstring states the
  contract; a test asserts the writeable flag is `False`.
- **Channel keys.** In-memory `dict[int, ImageContrast]`; string conversion
  occurs only inside `_build_sidecar_payload` / `_apply_loaded_sidecar_payload`.
- **Selection-change UX.** `ImageToolbarView` disables the contrast widget
  on every `(file_id, channel)` transition and re-enables it from
  `_on_plane_loaded`. The disabled state is the loading affordance.
- **Sidecar back-compat.** `_ACQIMAGE_SIDECAR_VERSION` remains `2`.
  `image_contrast` is treated as optional via
  `_ACQIMAGE_SIDECAR_OPTIONAL_KEYS`, so old v2 sidecars load cleanly with
  no unknown-key warning.

## Disabling sidecar persistence

Persistence of `image_contrast` is wrapped in
`# region image_contrast persistence` / `# endregion` markers in two places
inside `src/acqstore/acq_image/acq_image.py`. Comment out both region blocks
to use in-memory defaults only; the rest of the runtime continues to work
because `PrimaryPlaneLoaded` seeds fresh values per session.

## Concerns or follow-ups

- `PlotlyRasterViewer.set_heatmap_colorscale` is typed as `str`. The custom
  `inverted_grays` LUT (a `[[stop, color], ...]` list) is currently mapped
  to `'Greys'` inside `PrimaryImageView._apply_contrast` as a documented
  fallback. If the team wants true inverted gray, widening the viewer API
  would be the next step.
- `ContrastWidget` constructor draws NiceGUI elements eagerly. Construction
  in tests is fine, but creating one outside a NiceGUI client may not
  attach until built in a slot. The current `ImageToolbarView` builds
  inside `ui.row()` so this is unchanged from the existing toolbar pattern.
- One pre-existing Ruff warning (`E402` late import in `image_toolbar_view.py`)
  was left untouched per ticket-scope rules.
