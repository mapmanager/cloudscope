# Ticket 073 — Lazy `AcqImage` construction for CZI/OIR/TIF (header-only folder load)

**Status:** Planning (questions open — do not implement until answered)  
**Depends on:** `007_fix_primary_image_selection_orchestration_report.md` (pixel orchestration via `ImagePixelsController`) — complete  
**Recommended after:** Ticket 072 (spinner) — cold loads become frequent for all formats once lazy init lands

---

## Goal

Folder/file list construction should be **header + sidecar only**; full pixel volume loads on demand via existing `ImagePixelsController.ensure_loaded` → `load_image_data()` path.

---

## Current state (facts)

| Area | Today |
|------|--------|
| `AcqImage.__init__` | `self._pixels = self._images.load_pixels()` — always runs |
| `BaseFileLoader.load_pixels()` | Calls `load_image_data()` → full volume in memory |
| `BaseFileLoader._post_init` | `read_header()` only — header available without pixels |
| OME-Zarr | Overrides `load_pixels()` — Zarr-backed, lazy; `pixels_loaded()` false until `load_image_data()` |
| CZI/OIR/TIF | Loaders document lazy internal reads; **eager** at `AcqImage` construction |
| `AcqImageList` | `[AcqImage(path) for path in file_list]` — N full reads for N files |
| Init-time needs | `_infer_image_bounds()` uses header sizes only; `ImageHeaderMetadata` needs header only |
| CloudScope display | `get_slice_data_loaded` after `ensure_loaded` — already strict |
| Implicit loads in acqstore | `get_slice_data()`, `get_roi_rect_image()`, `get_channel_data()` call `load_image_data()` on first use |

---

## Target architecture

```text
Today:
  AcqImage.__init__
    → create_file_loader()     # header
    → load_pixels()
        → load_image_data()    # FULL READ (CZI/OIR/TIF)

Target:
  AcqImage.__init__
    → create_file_loader()     # header
    → metadata / ROIs / sidecar from header
    → pixels NOT loaded

  User selects file
    → ImagePixelsController.ensure_loaded
    → load_image_data()
    → FileSelectionChanged
    → primary slices via get_slice_data_loaded
```

---

## Work breakdown

### 1. `AcqImage.__init__` (`acqstore/acq_image/acq_image.py`)

- Stop calling `load_pixels()` eagerly.
- Build `ImageHeaderMetadata`, `RoiSet`, etc. from `self._images.header` (not `self._pixels.header`).
- Keep lazy `pixels` property coherent.

### 2. `BaseFileLoader.load_pixels()` (`base_file_loader.py`)

- Today always materializes data. Needs header-only / deferred path for CZI/OIR/TIF (OME-Zarr pattern).
- **Option A:** Change default `load_pixels()` to return `AcqPixels` without loading (data unset until `load_image_data`).
- **Option B:** Per-loader overrides (mirror `OmeZarrFileLoader`).
- **Decision required** before implementation.

### 3. Audit implicit loaders

- `get_slice_data()`, `get_roi_rect_image()`, `get_channel_data()` still implicit-load today.
- **Strict:** callers must call `load_image_data()` explicitly; fail-fast elsewhere.
- **Permissive:** keep implicit load in `get_slice_data()` for scripting.
- **Decision required.**

### 4. `pixels_loaded()` semantics

- `False` after construct; `True` after `load_image_data()`.
- OME-Zarr behavior unchanged.

### 5. `AcqImageList` / `load_safe`

- Folder open much faster (header-only per file).
- `progress_callback` messages may change (“opening metadata” vs “loading pixels”).

### 6. Tests and scripts

- Many `tests/acqstore` assume `AcqImage(path)` has pixels ready.
- Audit: which tests call `load_image_data()` explicitly vs assert `not pixels_loaded()`.
- Audit `scripts/acqstore/`.

---

## Risks

| Risk | Notes |
|------|--------|
| Scripts/notebooks break | `AcqImage(path)` may have `pixels_loaded() == False` immediately |
| Analysis before load | Ensure load or fail-fast before analysis tasks |
| Reference image (CZI) | Loads from attachment separately; verify when primary pixels unloaded |
| Memory | Folder load uses less RAM; **unload on file switch** may be needed later |
| TIFF without Olympus `.txt` | `read_header()` may still touch pixels — verify per loader |

---

## Likely files

- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/file_loaders/base_file_loader.py`
- Possibly `czi_file_loader.py`, `oir_file_loader.py`, `tiff_file_loader.py`
- `tests/acqstore/**` (large)
- CloudScope: few/no changes if 007 orchestration remains correct

---

## Open questions (must answer before implementation)

7. **All formats in one ticket** (CZI + OIR + TIF), or phased (e.g. TIF first)?
8. **Backward compatibility:** acceptable breaking change (`pixels_loaded() == False` after construct), or opt-in flag / deprecated eager mode?
9. **`get_slice_data()` policy:** keep implicit load for scripting, or fail-fast like `get_slice_data_loaded`?
10. **Analysis tasks:** should `acqstore` analysis implicit-load via `get_roi_image`, or should CloudScope ensure `load_image_data()` before analysis?
11. **Memory management:** unload previous file’s pixel cache on file switch? (Not MVP for lazy init, but increasingly relevant.)
12. **TIFF without Olympus `.txt`:** is partial TIFF metadata at init OK, or must init avoid **any** pixel IO?

### Sequencing (cross-ticket)

13. **Confirm order:** 072 spinner → 073 lazy init, or combine into one ticket?

---

## Acceptance criteria (draft — refine after Q&A)

- [ ] `AcqImage(path)` completes without full pixel read for CZI/OIR/TIF (per agreed format scope)
- [ ] `pixels_loaded()` is `False` immediately after construct (for affected formats)
- [ ] `load_image_data()` + `get_slice_data_loaded` unchanged contract
- [ ] `AcqImageList` folder load does not read full volumes for every file
- [ ] CloudScope file select still works via `ImagePixelsController` cold path
- [ ] OME-Zarr behavior unchanged
- [ ] Tests updated; `uv run pytest` green
- [ ] Ticket report under `docs-dev/codex_tickets/`

---

## How 072 and 073 interact

```text
Before 073:
  Folder open: slow (reads all pixels)
  File select (CZI/OIR/TIF): hot → spinner rarely seen
  File select (OME-Zarr): cold → spinner useful (072)

After 073:
  Folder open: fast (headers only)
  File select (all formats): often cold → spinner important (072)
```

Implement **072 before 073** unless combining tickets.
