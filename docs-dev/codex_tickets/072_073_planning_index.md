# Tickets 072 & 073 — planning index

**Purpose:** Persist plans and open questions for return to the original implementation chat after interim code work elsewhere.

**Created:** 2026-06-22 (post `007_fix_primary_image_selection_orchestration_report.md`)

**Note:** Originally drafted as 008/009; renumbered to follow repo convention (latest prior ticket: 071).

---

## Documents

| Ticket | Plan file |
|--------|-----------|
| 072 — Cold pixel load spinner | [072_primary_image_loading_spinner_plan.md](./072_primary_image_loading_spinner_plan.md) |
| 073 — Lazy `AcqImage.__init__` | [073_lazy_acq_image_init_plan.md](./073_lazy_acq_image_init_plan.md) |

---

## Recommended order

1. **072** — Loading spinner (CloudScope; smaller; helps OME-Zarr now)
2. **073** — Lazy `AcqImage` init (`acqstore`; larger; makes cold loads normal for all formats)

---

## All open questions (checklist)

Answer before implementing either ticket:

### 072 — Spinner

1. Spinner location: primary overlay (A) / page composer (B) / global busy (C)?
2. OK with narrow loading state event despite 007 selection-only refresh?
3. Primary only, or reference image too?
4. File table interactive during cold load?
5. Behavior on load failure?
6. Cancel in-flight pixel load?

### 073 — Lazy init

7. All formats at once or phased?
8. Breaking change OK, or compat flag?
9. `get_slice_data()` implicit load vs fail-fast?
10. Analysis: implicit load in acqstore vs CloudScope ensures load?
11. Unload previous file pixels on switch?
12. TIFF without Olympus `.txt` — any pixel IO at init allowed?

### Sequencing

13. 072 then 073, or combined ticket?

---

## Context from ticket 007 (complete)

Report: `007_fix_primary_image_selection_orchestration_report.md`

- `ImagePixelsController.ensure_loaded` → `on_complete` → `FileSelectionChanged`
- Primary refreshes via `on_primary_selection_changed` only
- Cold load: keep previous image on screen until selection event
- `ImagePixelsReady` removed

---

## When returning to implement

1. Read answers to questions 1–13 (update plan files with decisions).
2. Implement 072 per chosen option; run `uv run pytest`; write `072_*_report.md`.
3. Implement 073 per chosen scope; run full pytest; write `073_*_report.md`.
