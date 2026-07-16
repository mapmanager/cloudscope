# 055 — Handoff: OIR line-scan Y time step (not spatial scale)

**Type:** Handoff / planning (implementation on `main`)  
**Status:** Ready for implementation on branch `main`  
**Related:** `038_oir_skip_channel_physical_units_report.md` (C/S skip + Y→seconds label only)

---

## Diagnosis (verified on feature/acqstore_server)

### Symptom (acqstore_server JSON — not a server bug)

For line-scan OIR `tmp/Example OCaMP-FITC Data/20260709_A131_0006.oir`, open JSON
`calibration` reported:

```json
"dim_0_step": 0.0009662322285482559,
"dim_1_step": 0.0009662322285482559,
"dim_0_units": "seconds",
"dim_1_units": "micrometer"
```

Units differ (correct indices); steps are identical.

### Server is a faithful passthrough

`acqstore_server.open_service._calibration_from_acq` maps:

- `dim_0_step` ← `get_image_physical_units()[0]` ← header `physical_units[Y]`
- `dim_1_step` ← `get_image_physical_units()[1]` ← header `physical_units[X]`
- `dim_*_units` ← `physical_units_labels[Y|X]`

No server indexing bug. Do **not** invent different steps in `acqstore_server`.

### Root cause in acqstore OIR loader

File: `src/acqstore/acq_image/file_loaders/oir_file_loader.py`

`_physical_units_for_oir_header`:

1. Detects TIMELAPSE-on-Y line scan via `_is_y_timelapse_line_scan_axis`.
2. Relabels **Y** as `"seconds"`.
3. Still uses **`coord_scales['Y']`** as the Y step (same spatial scale path as X).

For the OCaMP file, `oirfile` reports:

| Field | Value |
|---|---|
| dims | `('C', 'Y', 'X')` |
| `coord_scales` | `Y` and `X` both `0.000966…` |
| `coord_units` | both `'micrometer'` originally |
| TIMELAPSE axis | `enable=True`, `maxSize=10000`, **`step=0.0`** |
| AcqImage header after load | `physical_units=(1.0, 0.000966…, 0.000966…)`, labels `('Pixels', 'seconds', 'micrometer')` |

So Y is labeled time but still carries a spatial (or duplicated) scale. That is why
`dim_0_step == dim_1_step` while units look correct.

### Scope of fix

| In scope | Out of scope |
|---|---|
| `oir_file_loader.py` (`_physical_units_for_oir_header` and helpers as needed) | `acqstore_server` / demo HTML |
| `tests/acqstore/test_oir_file_loader.py` | Inventing steps in server JSON |
| Ticket report on `main` when implemented | Other loaders unless same bug found |

`acq_image.py` is not the bug source; it only exposes header spacing via
`get_image_physical_units()`.

---

## Intended fix (implement on `main`)

**Goal:** When Y is a TIMELAPSE line-scan axis, set **Y step from a true time
source**; keep **X** from spatial `coord_scales['X']` (or existing spatial path).

Then `get_image_physical_units()` → server `calibration.dim_*` automatically
diverge when time ≠ space.

### Open: true time source (must resolve on `main` — do not guess)

TIMELAPSE `step` is `0.0` for the failing OCaMP file, so it is **not** yet a
usable source of truth.

On `main`, determine with laser focus (inspect LSMIMAGE XML, oirfile public/private
fields, Olympus docs, known-good duration/line-rate metadata, etc.) and document
the chosen source in the implementation report.

Until that source is named and verified, do not implement a guessed formula.

### Existing tests that encode current (label-only) behavior

These currently expect Y step to remain `coord_scales['Y']` after relabel — they
must be updated once the time source is known:

- `test_physical_units_for_oir_header_relabels_y_for_line_scan_kymograph`
- `test_physical_units_for_oir_header_skips_coords_when_scales_complete`
- `test_physical_units_for_oir_header_skips_channel_dim_c` (equal Y/X scales case)
- Fixture test `test_oir_kymograph_fixture_labels_y_seconds_x_um` (may already have
  unequal scales; re-check expected Y step against new time source)

Add an explicit unit test where `coord_scales['Y'] == coord_scales['X']` but the
true time step differs (once known).

---

## Git workflow (user runs all git commands)

Current branch `feature/acqstore_server` stays as-is (server work). Implementation
happens on `main`.

```bash
# 1. Ensure feature branch is clean, then switch
git status
git switch main
git pull origin main

# 2. Implement + test on main (agent or human)
#    - resolve true Y time source (100% SoT)
#    - patch oir_file_loader.py
#    - update tests/acqstore/test_oir_file_loader.py
uv run pytest tests/acqstore/test_oir_file_loader.py

# Optional smoke (local OIR, not committed):
# uv run python -c "from acqstore.acq_image.acq_image import AcqImage; ..."

# 3. User commits and pushes main (no PR)
git add -A
git commit -m "..."   # user writes message
git push origin main

# 4. Merge back into feature branch
git switch feature/acqstore_server
git merge main
# resolve conflicts if any
uv run pytest tests/acqstore/test_oir_file_loader.py
# optionally: tests/acqstore_server/ for calibration passthrough still OK
```

---

## Success criteria

- Line-scan OIR header: `physical_units_labels[Y] == "seconds"`, X remains spatial label.
- Y step comes from documented true time source; X step remains spatial.
- For OCaMP-style files where `coord_scales` Y/X were equal, Y and X steps are
  correct per SoT (not merely “not equal” unless SoT says they differ).
- Unit tests updated and green: `uv run pytest tests/acqstore/test_oir_file_loader.py`
- No `acqstore_server` changes required for `calibration.dim_*` to improve.

---

## Files changed (this handoff only)

- `docs-dev/cursor_tickets/055_oir_linescan_y_time_step_handoff.md`

## Implementation report (later, on `main`)

Create a new numbered implementation report (e.g. `056_…`) when the fix lands;
include chosen time source, files changed, tests, and commands.
