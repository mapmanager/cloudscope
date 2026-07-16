# 061 — Upstream oirfile issue/PR: OIR physical calibration (handoff / planning)

**Type:** handoff / upstream-contribution planning (no acqstore code changes in
this ticket).

**Goal:** File a GitHub issue on
[cgohlke/oirfile](https://github.com/cgohlke/oirfile) describing incorrect
X/Y physical scaling and a missing line-scan time axis, ask the maintainer if
a PR is welcome, and (if yes) submit a focused PR. Draft issue text is at the
bottom of this ticket.

**Context version:** `oirfile==2026.7.10` (current PyPI release; identical to
upstream `main` at commit `21bc6c5`, 2026-07-09).

---

## 1. Problem statement

`oirfile` parses the per-pixel physical size from OIR LSMIMAGE XML:

```text
imageProperties/.../channel/length/x   = 0.331456303681194
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
exports) proves the XML value is **already µm/pixel**:

```text
"X Dimension"  "512, 0.0 - 169.706 [um], 0.331 [um/pixel]"
```

`169.706 / 512 = 0.331457` — i.e. FluoView itself reports
`total = pixel_length * n_pixels`, so `pixel_length` is the per-pixel step.
`co