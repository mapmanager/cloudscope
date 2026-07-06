# How to fix PNG ↔ heatmap transition flash

Self-contained implementation roadmap for reducing or eliminating visible flash when the raster viewer switches between `image_png` and `heatmap_z` during pan/zoom. Read this before starting the ticket; it assumes the **viewport observer** work from ticket 001 is already merged.

---

## Problem statement

During wheel zoom or viewport settle, `RasterViewService.choose_mode()` may switch:

- **Zoomed out / large clip** → `image_png` (encoded overview)
- **Zoomed in / small clip** → `heatmap_z` (numeric array)

Today, a cross-type update uses `Plotly.react(plotDiv, data, plotDiv.layout, config)` in `PlotlyRasterViewer.apply_response()`. That replaces trace 0’s type (`image` ↔ `heatmap`), which can produce a visible flash even when axis ranges are preserved.

**In scope:** mode-switch flash on the wheel/viewport path.

**Out of scope (separate tickets):**

- Wheel zoom flicker from axis relayout feedback (fixed in ticket 001)
- Pyramid spatial truncation / top-y misalignment (ticket 002)
- 1D chart ↔ primary x-range sync
- pywebview trackpad context menu (ticket 003)

---

## Current architecture (after ticket 001)

```text
Plotly owns viewport (x/y axis ranges in browser)
     ↓ debounced settle (~120ms)
_read_live_viewport_from_browser()
     ↓
RasterViewService.render(bounds, viewport)
     ↓
apply_response()
  same trace type  → Plotly.restyle(trace 0)     ← smooth
  PNG ↔ heatmap    → Plotly.react(data, layout)  ← flash risk
  set_data / reset → _plot.update()              ← full rebuild OK
```

Key files:

| File | Role |
|------|------|
| `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py` | `apply_response`, `_can_restyle_raster_trace`, `_react_plotly_data_preserving_browser_layout` |
| `src/nicewidgets/raster_viewer/backend/raster_service.py` | `choose_mode()` threshold `heatmap_max_values` (default 500k) |
| `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py` | `build_plotly_figure`, trace layout |
| `tests/nicewidgets/test_plotly_viewer_state.py` | apply/restyle/react tests |

---

## Target architecture: dual trace (Option 2)

**Rule:** Never swap trace *type* on the wheel path. Keep both raster representations in the figure; toggle visibility and restyle the active trace.

```text
data[0] = PNG image trace   (always present after scaffold)
data[1] = heatmap trace     (always present after scaffold)
data[2+] = overlays         (indices shift — refactor trace index constants)
```

Mode switch becomes:

```text
visibility flip + restyle active trace payload
NO Plotly.react cross-type on viewport settle
```

---

## Phased implementation

### Phase 0 — Characterize (manual, ~1 hour)

Before coding, record short screen captures or notes:

| Gesture | Direction | Flash? | Mode before → after |
|---------|-----------|--------|---------------------|
| Wheel zoom in | PNG → heatmap | | |
| Wheel zoom out | heatmap → PNG | | |
| X-drag only | | | |
| Double-click reset | | | |

Log `render()` mode/level lines (already in `raster_service.py`) during each case.

**Exit criteria:** Confirm flash correlates with `apply_response` react branch (`test_apply_response_uses_plotly_react_for_cross_type` in `test_plotly_viewer_state.py`).

---

### Phase A — Mode hysteresis (backend, ~0.5 day)

**Goal:** Reduce boundary oscillation when clip size hovers near `heatmap_max_values`.

In `RasterViewService.choose_mode()`:

- Enter heatmap when `clip.size <= ENTER_THRESHOLD` (e.g. 400k)
- Stay in / return to PNG only when `clip.size > EXIT_THRESHOLD` (e.g. 550k)
- Require `last.mode` from viewer state or pass previous mode in `ViewRequest` (needs explicit API — **design choice**)

**Friction:**

- Viewer must pass last applied mode into render request, or service stores last mode per viewer instance (service is stateless today — prefer viewer-side hysteresis wrapper before calling `render()`).

**Tests:** `tests/nicewidgets/test_raster_service.py` — oscillation around threshold does not flip mode every frame.

---

### Phase B — Dual-trace scaffold (~1 day)

**Goal:** Figure always contains PNG + heatmap traces; overlays use fixed indices.

1. Add constants, e.g. `RASTER_PNG_TRACE_INDEX = 0`, `RASTER_HEATMAP_TRACE_INDEX = 1`, `OVERLAY_TRACE_BASE = 2`.
2. Change `build_plotly_figure()` to accept `mode` but emit **both** traces (inactive trace: empty `source` / minimal `z`, `visible: false`).
3. Update `_replace_local_raster_trace`, `_restyle_raster_trace0_from_plotly_dict`, overlay sync, ROI shapes (unchanged in layout).
4. Initial `set_data` / overview still PNG-visible, heatmap hidden.

**Friction:**

- Trace overlay indices today assume raster at 0 — grep `_set_trace_overlay_visibility`, `data[0]`.
- `copy_plot_to_clipboard`, hover, contrast restyle target “active” trace — audit all `data[0]` assumptions.

**Tests:** `build_plotly_figure` returns two raster traces; inactive trace `visible: false`.

---

### Phase C — Visibility-only mode switch on viewport path (~1 day)

**Goal:** Remove cross-type `Plotly.react` from `_refresh_raster_for_viewport` / `apply_response` when `display_axis_ranges` is set.

1. Extend `apply_response`:
   - Same dual-trace figure: restyle PNG trace and/or heatmap trace + set `visible` flags via `Plotly.restyle` or one `Plotly.update` **without** layout keys.
2. Delete or bypass `_react_plotly_data_preserving_browser_layout` on wheel path.
3. Keep `react`/`update` for `set_data`, theme, double-click reset if simpler.

**Friction:**

- PNG and heatmap must cover **same physical extent** (ticket 002 coverage logic) or flash becomes misalignment, not just brightness.
- Memory: two traces × large payloads — usually OK because one is PNG URI, one is numeric; still watch overview PNG size.

**Tests:** Update `test_apply_response_uses_plotly_react_for_cross_type` → expect dual restyle/visibility, not react.

---

### Phase D — Manual sign-off + ticket report (~0.5 day)

Manual matrix (browser + Option C desktop):

- [ ] Wheel zoom in/out — no flash at mode boundary
- [ ] PNG/heatmap data matches (no stale strip at edges)
- [ ] ROI overlays still index correctly
- [ ] Trace overlays visible/hidden toggles
- [ ] Context menu, copy-to-clipboard
- [ ] Double-click reset

Report under `docs-dev/codex_tickets/00N_dual_trace_mode_switch_report.md`.

---

## Failure modes and mitigations

| Risk | Symptom | Mitigation |
|------|---------|------------|
| Trace index drift | Overlays on wrong trace | Centralize index constants; grep `data[0]` |
| Hysteresis without state | Still oscillates PNG/heatmap | Viewer passes `_last_applied_response.mode` into choose logic |
| Dual trace memory | Slow initial load | Lazy-build hidden trace on first mode switch |
| Coverage bug | Edge misalignment at mode switch | Run ticket 002 tests before Phase C |
| `Plotly.restyle` partial update | Missing `z` or `source` | Restyle full trace dict for target index |
| ROI edit + dual trace | Shape drag oddities | Manual test in edit mode; unrelated to flash but same file |
| Packaged pywebview | Different perf | Include desktop in sign-off |

---

## Alternative considered: accept flash

If dual trace is too invasive:

- **Phase A only** (hysteresis) may be enough for UX if flash is rare.
- Increase `heatmap_max_values` to stay PNG longer (tradeoff: more PNG encodes).

Document decision in ticket report if stopping after Phase A.

---

## Related completed work

| Ticket | Topic |
|--------|--------|
| 001 | Wheel zoom flicker — viewport observer, x-only `set_x_axis_range`, restyle path |
| 002 | Pyramid `choose_level` coverage — spatial extent at y-max |
| 003 | pywebview trackpad context menu on Plotly canvas |

---

## Suggested test commands

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py tests/nicewidgets/test_raster_service.py -q
uv run pytest tests/nicewidgets/ -q
uv run pytest
```

---

## Estimated effort

| Phase | Effort |
|-------|--------|
| 0 Characterize | 1 h |
| A Hysteresis | 0.5 d |
| B Dual-trace scaffold | 1 d |
| C Visibility switch | 1 d |
| D QA + report | 0.5 d |
| **Total** | **~3–4 days** |

Implement phases in order; do not start Phase C before Phase B tests pass.
