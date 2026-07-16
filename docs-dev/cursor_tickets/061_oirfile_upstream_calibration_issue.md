# 061 — Upstream oirfile issue/PR: OIR physical calibration (handoff)

**Type:** handoff / upstream-contribution planning. No acqstore code changes.

**Goal:** File a GitHub issue on
[cgohlke/oirfile](https://github.com/cgohlke/oirfile) describing incorrect
X/Y physical scaling and a missing line-scan time axis, ask the maintainer if
a PR is welcome, and (if yes) submit a focused PR. Draft issue text is in
section 8.

**Context version:** `oirfile==2026.7.10` (current PyPI release; identical to
upstream `main` commit `21bc6c5`, 2026-07-09).

---

## 1. Problem statement

`oirfile` parses the per-pixel physical size from OIR LSMIMAGE XML:

```text
imageProperties/.../channel/length/x    = 0.331456303681194
imageProperties/.../channel/pixelUnit/x = MICRO_METER
```

and stores it as `OirFile._pixel_length_x` / `_pixel_length_y`. But the
public coordinate APIs then **divide this value by the axis size**, treating
it as a total field extent instead of a per-pixel step:

```python
# OirFile.coords / coord_scales (oirfile.py, v2026.7.10)
result['Y'] = self._pixel_length_y / self._frame.height
result['X'] = self._pixel_length_x / sizes['X']

# OirReference.coord_scales
result['Y'] = ply / self._height
result['X'] = plx / self._width
```

The Olympus/Evident export TXT sidecar (written by FluoView alongside TIF
exports) shows the XML value is **already micrometers per pixel**:

```text
"X Dimension"  "512, 0.0 - 169.706 [um], 0.331 [um/pixel]"
```

`169.706 / 512 = 0.331457`, i.e. FluoView reports
`total_um = pixel_length * n_pixels`, so `pixel_length` is the per-pixel
step. Dividing it again by the pixel count makes `coord_scales` wrong by a
factor of the axis size (24x to 512x on our files).

A second, related gap: line-scan (kymograph) OIR files store TIMELAPSE on
the `Y` axis (one scan line per time step). `oirfile` labels `Y` as
`micrometer` with the (already wrong) spatial step; the true per-line period
is in LSMIMAGE `seriesInterval` (milliseconds), which `oirfile` does not
parse.

---

## 2. Evidence (measured on our files)

### 2.1 Kymograph `tests/acqstore/data/oir-samples/20251030_A106_0002.oir` (X=24, Y=30000)

| Quantity | Value | Source |
|---|---|---|
| XML `length/x` (`_pixel_length_x`) | 0.274 um/px | LSMIMAGE `imageProperties` |
| `oirfile.coord_scales()['X']` | 0.274 / 24 ≈ **0.0114** | wrong (÷ size) |
| True per-line period | 1.142 ms/line → 0.001142 s | `seriesInterval` (active Galvano scanner) |
| `oirfile.coord_scales()['Y']` | spatial value ÷ 30000, labeled micrometer | wrong axis meaning |

Pinned by `test_oir_kymograph_fixture_labels_y_seconds_x_um` (expects
`0.001142` s and `0.274` um after our workarounds).

### 2.2 Reference image in `tmp/oir-debug/two-channel-oir/20260709_A131_0010.oir` (512x512)

| Quantity | Value | Source |
|---|---|---|
| Parent `_pixel_length_x` | 0.331456 um/px | LSMIMAGE XML |
| TXT "X Dimension" | 169.706 um total, 0.331 um/pixel | Olympus TXT |
| `OirReference.coord_scales()['X']` | 0.331456 / 512 = **0.000647** | wrong (÷ size) |

Pinned by `test_oir_debug_0010_reference_matches_primary_x_and_txt_um_per_pixel`
(expects reference dx == 169.706 / 512 after our workarounds).

In both cases the XML value matches the vendor's own um/pixel figure
exactly; only the division by axis size in `oirfile` breaks it.

Note: `OirReference` uses the **reference image's own** width/height as the
divisor but the **parent primary image's** pixel length as the numerator, so
the reference result is doubly incoherent — the correct reference um/px is
the parent per-pixel step scaled by (parent extent / reference size), which
for our files equals the parent per-pixel value when reference and primary
cover the same field.

---

## 3. Current acqstore workarounds (what we would delete if fixed upstream)

All in `src/acqstore/acq_image/file_loaders/oir_file_loader.py`:

1. **`_physical_units_for_oir_header()`** — ignores
   `OirFile.coord_scales()` entirely. Reads `_pixel_length_x` /
   `_pixel_length_y` directly for spatial axes.
2. **`_is_line_scan_scene()` + `_line_scan_y_step_seconds_from_scene()`** —
   detects TIMELAPSE-on-Y line scans and re-parses the raw LSMIMAGE XML
   (`OirFile.xml_lsm()`) to extract `seriesInterval` values, converting the
   selected value from ms to seconds for the Y axis.
   - Selection heuristic (ours, not oirfile's): minimum positive
     `seriesInterval` < 30 ms. Works on our files; brittle in general. The
     deterministic form is to match `scannerSettings[type]` against the
     active `scannerType` (e.g. `Galvano` vs `Resonant`) and take that
     scanner's `seriesInterval`.
3. **`_oir_reference_spatial_coord_scales()`** — overrides
   `OirReference.coord_scales()` for reference snapshots, substituting the
   parent `_pixel_length_x/y` per-pixel values.

Tests pinning the workarounds: `tests/acqstore/test_oir_file_loader.py`
(exact-value comparisons against Olympus TXT sidecars).

---

## 4. Proposed upstream changes

### 4.1 Bug fix: stop dividing pixel length by axis size

In `OirFile.coords()` / `coord_scales()` and
`OirReference.coords()` / `coord_scales()`:

```python
# before
result['X'] = self._pixel_length_x / sizes['X']
# after
result['X'] = self._pixel_length_x
```

For `OirReference`, the correct value depends on intent:

- If reference and primary share the field of view (our observed case),
  reference um/px = `parent_pixel_length * parent_size / reference_size`.
- The reference XML block may carry its own length values; if present,
  those should be preferred over the parent's.

This is a **behavior change** for anyone consuming `coord_scales`, so the
maintainer may prefer a major-version bump or a changelog callout.

### 4.2 Enhancement: line-scan time axis

- Detect line-scan acquisitions (axis order/`TIMELAPSE` on Y, or
  `lsmimage speedInformation`).
- Parse `seriesInterval` per scanner from LSMIMAGE XML and select the entry
  whose `scannerSettings[type]` matches the active `scannerType`.
- Report Y as seconds (or milliseconds, documented) in `coords` /
  `coord_scales`, with the unit exposed alongside (oirfile currently has no
  per-axis unit API — that may need a small addition, e.g.
  `coord_units()`).

### 4.3 Suggested tests upstream

- Exact-value asserts against files whose FluoView TXT sidecars are known
  (we can contribute anonymized values from our files):
  - primary X um/px == XML `length/x` (no division),
  - reference um/px consistent with TXT total-extent line,
  - kymograph Y step == matched `seriesInterval` / 1000.

---

## 5. Risks / open questions for the maintainer

1. **Intentional semantics?** `coords()` docstrings say the values are
   coordinate arrays; maybe the author intended normalized 0..length
   coordinates. The division still contradicts the vendor TXT, but the fix
   shape depends on the intended contract.
2. **Backward compatibility.** Downstream users may have already
   compensated (as we did). A changelog note and version bump are needed.
3. **Reference semantics.** We only have files where reference and primary
   share the field of view; other hardware may differ. The maintainer may
   have counterexample files.
4. **Time-axis unit API.** Adding seconds to `coord_scales` without a unit
   accessor is ambiguous; propose `coord_units()` or documenting the rule.

---

## 6. Recommended approach

1. Comment on the existing closed upstream issue about calibration
   (cgohlke/oirfile#3) or open a new issue using the draft in section 8.
2. Ask explicitly whether a PR is welcome (single-maintainer repo;
   cgohlke's repos usually take patches via issue discussion first).
3. If welcomed, submit one PR with two logical commits:
   - commit 1: spatial per-pixel scaling fix (`OirFile` + `OirReference`)
     with exact-value tests,
   - commit 2: line-scan time-axis calibration (`seriesInterval` matching
     by active scanner type) with tests.
4. After an upstream release, open an acqstore ticket to bump the pinned
   `oirfile` version and delete the workarounds in section 3.

---

## 7. What stays in acqstore regardless

- Mapping to OME/NGFF-style axis labels and `AcqPixels` metadata.
- The `ReferenceImage` snapshot / `ReferenceImageMetadata` schema.
- Sidecar TXT cross-checks in our tests (they validate any oirfile
  version we ship).

---

## 8. Draft GitHub issue text

> **Title:** coord_scales divides pixel length by axis size; line-scan time
> axis not calibrated
>
> Thanks for oirfile — we use it in a lab acquisition tool and hit two
> calibration issues with `coord_scales()` (v2026.7.10).
>
> **1. Spatial scale divided by axis size.** LSMIMAGE
> `imageProperties/.../channel/length/x` appears to already be micrometers
> per pixel, not a total extent. Evidence: for a 512x512 acquisition the
> FluoView-exported TXT sidecar reports
> `"X Dimension" "512, 0.0 - 169.706 [um], 0.331 [um/pixel]"` and the XML
> `length/x` is `0.331456...` — i.e. `total = length * n_pixels`. But
> `OirFile.coord_scales()` computes `_pixel_length_x / sizes['X']`,
> yielding `0.000647` um/px (512x too small). `OirReference.coord_scales()`
> has the same division using the reference's own width/height with the
> parent's pixel length.
>
> Suggested fix: return `_pixel_length_x` / `_pixel_length_y` directly (and
> for references, scale by parent extent / reference size or use
> reference-local length values when present).
>
> **2. Line-scan (kymograph) Y axis is time, not micrometers.** For
> TIMELAPSE-on-Y line scans, the per-line period is in LSMIMAGE
> `speedInformation` `seriesInterval` (ms), selectable by matching
> `scannerSettings[type]` to the active `scannerType`. oirfile currently
> reports the (divided) spatial value labeled micrometer for Y. We
> currently re-parse `xml_lsm()` downstream to get this.
>
> We have test files with vendor TXT sidecars and can share exact expected
> values. Would you accept a PR for either or both of these? Happy to keep
> the changes small and add exact-value tests.

---

## 9. Status

- [x] Analysis complete (this ticket)
- [ ] File upstream issue (user action — draft above)
- [ ] Maintainer response / PR go-ahead
- [ ] PR with two commits (if welcomed)
- [ ] Post-release acqstore cleanup ticket

Handoff ticket: no repository code changes, no tests run.
