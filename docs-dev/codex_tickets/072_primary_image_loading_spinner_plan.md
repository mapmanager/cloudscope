# Ticket 072 — Primary image loading indicator during cold pixel fetch

**Status:** Planning (questions open — do not implement until answered)  
**Depends on:** `007_fix_primary_image_selection_orchestration_report.md` (selection orchestration) — complete  
**Blocks / pairs with:** Ticket 073 (lazy `AcqImage.__init__`) — 073 makes cold loads common for all formats; 072 should land first

---

## Goal

When `ImagePixelsController` loads pixels off the UI thread (cold path), show clear loading feedback **without** breaking the ticket 007 selection model.

---

## Current state (facts)

| Area | Today |
|------|--------|
| Orchestration | `HomePageController` → `ImagePixelsController.ensure_loaded` → `FileSelectionChanged` → `PrimaryImageView.on_primary_selection_changed` |
| Cold-load UX | Previous image stays visible until `FileSelectionChanged`; **no spinner** |
| Hot path | CZI/OIR/TIF: `pixels_loaded()` true after `AcqImage.__init__` (eager) — cold path rare |
| OME-Zarr | `pixels_loaded()` false until `load_image_data()` — cold path common today |
| Primary view | `disable_when_busy = False`; idle label + `clear_data()` when no selection |
| Global busy | `AppBusyChanged` + `TaskProgressDialogView` for `TaskKind` (load/save/analysis) |

---

## Architectural tension (007 constraint)

007 rule: **primary view listens to canonical selection only** (`FileSelectionChanged`), not pixel orchestration.

During cold load:
- `HomePageController` internal selection is already updated
- `FileSelectionChanged` is **not** published yet
- Primary still shows the **previous** file

Spinner **cannot** be driven purely from `FileSelectionChanged` or `on_primary_selection_changed` without one of:

1. A **narrow loading signal** (new state event or callback)
2. Spinner owned **outside** `PrimaryImageView` (page composer overlay)
3. Relaxing 007’s “primary doesn’t know pixel load” rule **for loading UI only**

---

## Design options (pick one)

### Option A — Local overlay on primary panel (leaning recommendation)

- Spinner + “Loading image…” in `PrimaryImageView` (same overlay area as idle label).
- Driven by minimal loading state from `ImagePixelsController` or `HomePageController`:
  - e.g. `ImagePixelsLoadStarted(file_id)` / `ImagePixelsLoadFinished(file_id)`, or
  - `ImagePixelsLoadingChanged(file_id | None)`
- Show spinner while load in flight for pending selection; hide on complete/stale/clear.
- **Do not** use `AppBusyChanged` (disables file table, image toolbar, etc.).

**Pros:** Obvious UX, localized, matches “keep previous image.”  
**Cons:** Slight exception to “primary only knows selection.”

### Option B — Page-level overlay (strictest 007 compliance)

- Composer adds semi-transparent overlay over primary panel.
- Subscribes to loading events; `PrimaryImageView` unchanged.

**Pros:** Primary stays selection-only.  
**Cons:** More composer wiring.

### Option C — Reuse `AppBusyChanged` / task progress dialog

**Not recommended** unless global lockout is desired (disables interactions; modal is heavy per file click).

---

## Proposed scope

### In scope

- Spinner during `ensure_loaded` **cold path only** (not hot/synchronous path)
- Primary panel feedback (unless Option B chosen)
- Stale-load guard already in controller; spinner must clear on stale completion
- Tests: loading state published; view shows/hides spinner

### Out of scope (unless explicitly added)

- Cancel in-flight pixel load
- Progress percentage
- Reference image spinner
- Folder-load spinner (separate from per-file pixel load)

---

## Likely files

- `src/cloudscope/controllers/image_pixels_controller.py` and/or `home_page_controller.py` — emit loading state
- `src/cloudscope/views/primary_image_view.py` (or page composer) — overlay UI
- `src/cloudscope/events/` — new small state event module (if Option A/B)
- `tests/cloudscope/`

---

## Open questions (must answer before implementation)

1. **Where should the spinner live?** Primary overlay (A), page composer overlay (B), or global busy/dialog (C)?
2. **OK with a narrow loading state event** (`ImagePixelsLoadingChanged` or similar), despite 007 keeping pixel events out of primary *refresh* logic?
3. **Scope:** primary only, or also reference image when slow?
4. **During cold load, file table stays interactive?** (allow rapid file switching) or block selection until load completes?
5. **On load failure** (controller skips `FileSelectionChanged` today): show error + keep previous image, clear primary, or notify only?
6. **Cancel:** should users cancel in-flight pixel load when switching files? (Stale-generation ignore exists; no cancel today.)

---

## Acceptance criteria (draft — refine after Q&A)

- [ ] Cold pixel load shows visible loading indicator without publishing `FileSelectionChanged` early
- [ ] Hot path (pixels already loaded) shows no spinner
- [ ] Previous image remains visible during load (007 behavior preserved)
- [ ] Spinner clears on successful load, stale load abandon, and clear selection
- [ ] Does not publish `AppBusyChanged` for pixel load (unless product chooses Option C)
- [ ] Tests cover controller loading signals and view show/hide behavior

---

## Relationship to ticket 073

After lazy `AcqImage.__init__`, **every** format may hit cold load on file select → spinner becomes essential for CZI/OIR/TIF, not just OME-Zarr. Implement 072 before or alongside 073.
