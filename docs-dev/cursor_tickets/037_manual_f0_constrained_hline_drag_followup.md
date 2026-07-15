# 037 — Manual F0 constrained H-line drag (follow-up)

## Status

**Handoff / follow-up.** Not implemented. Current Edit F0 Manual line is
acceptable: on mouse-up it snaps to a full-width horizontal line. Live drag
UX remains poor.

## Problem (current UX)

While dragging the Manual F0 measurement shape on the Edit F0 Plotly plot:

1. The line can become **diagonal** (endpoints move independently).
2. The user can drag in **X** as well as Y.
3. Visually it often looks like only the **first endpoint** moves.

On release, existing normalize (ticket 035) restores:

- `y0 == y1` (horizontal)
- `xref=paper`, `x0=0`, `x1=1` (full plot width)

## Desired UX

- Always a **horizontal** line spanning the **entire x-axis** (paper width).
- Drag is **Y-only**: both endpoints move together.
- No X translation or endpoint-skew during the gesture (not only on release).

## Why Plotly native shapes are insufficient

Plotly’s `config.edits.shapePosition` / shape editor treats a `type: "line"`
shape as a free two-point segment. There is no first-class “H-line, lock X,
translate Y only” mode. Ticket 035 CSS (disable vertex circles) +
post-relayout normalize improve commit behavior but do **not** fully constrain
the in-gesture visual.

Authoritative limitation: Plotly shape editing does not expose axis-locked
line drag ([community / shape edit discussion](https://community.plotly.com/t/moving-shapes-with-mouse-in-plotly-js-reactjs/11457)).

## Recommended approaches (for the implementation ticket)

Pick the smallest approach that meets the UX goal; prefer nicewidgets
ownership so CloudScope stays a thin consumer.

### Option A — Mid-drag normalize (try first, KISS)

On every `plotly_relayout` that touches the Manual shape, immediately
`Plotly.relayout` the normalized H-line (current `_normalize_measurement_shape`
+ `_push_shapes`). May feel jittery or fight Plotly’s drag, but is the
smallest change. Abort if interaction is worse than snap-on-release.

### Option B — Custom Y-only drag (recommended if A fails)

Do **not** use an editable Plotly shape for Manual F0. Instead:

1. Draw Manual F0 as a non-editable shape or line **trace** (full width).
2. Overlay a thin horizontal hit target (or pointer capture on the plot) with
   custom JS / NiceGUI events that map pointer Y → data Y and update the
   line via relayout/restyle.
3. Restrict motion to Y; keep `x` at paper 0–1 always.

This is more code but matches the product constraint exactly. Own it in
`nicewidgets.plotly_plot` (e.g. `add_y_locked_hline(...)`) rather than in the
sum-intensity view.

### Option C — Out of scope / reject

Keep snap-on-release only if product accepts the live diagonal as
“acceptable tech debt.” Document in UI help if users complain.

## Acceptance criteria (future implementation)

- [ ] During drag, Manual F0 never appears diagonal.
- [ ] During drag, line x-span stays full plot width (no X shift).
- [ ] Both visual ends move with the same Y continuously.
- [ ] On release, `manual_f0` pending value matches that Y.
- [ ] Unit tests for the public API; live native verify on Edit F0 plot.

## Out of scope for this follow-up

- Auto F0 (already a non-editable line trace).
- AcqStore detection-param changes.
- Edit F0 toolbar / live Set behavior.

## Related tickets

- 033 / 035 — snap-on-release normalize + vertex CSS attempt
- 034 — dual-plot Edit F0

## Recommendation

File an **implementation** ticket when ready to prioritize UX polish. Start
with Option A in a short spike; if the drag feels worse, implement Option B
in nicewidgets as a dedicated Y-locked H-line API.
