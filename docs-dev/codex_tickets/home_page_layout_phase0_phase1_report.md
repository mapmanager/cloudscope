# Home page layout Phase 0+1 report

## Files changed

- `src/cloudscope/pages/home_page.py`

## Summary of implementation

**Phase 0:** Root home splitter height now subtracts footer space
(`calc(100vh - 4rem - 2rem)`), matching the pool page pattern. Reduces
accidental page overflow / wheel nudge caused by header + main + footer
exceeding viewport height.

**Phase 1:** `_sync_analysis_reference_layout()` no longer squashes the
reference splitter pane when the Reference SmartExpansion is collapsed.
When analysis is visible, the remembered analysis/reference split is
restored so the expansion header stays reachable. Reference-only layout
still collapses the analysis pane (`before`) to give reference full height.

## Tests added or modified

None (layout-only home page change).

## Exact test commands run

Not run (no automated coverage for home page layout).

## Test results

N/A — manual check: no vertical page nudge on wheel; Reference image
SmartExpansion header reachable when collapsed.

## Concerns or follow-ups

- `2rem` footer allowance is approximate; tune if footer height changes.
- Phase 2 (unified scroll for analysis + reference stack) not implemented.
