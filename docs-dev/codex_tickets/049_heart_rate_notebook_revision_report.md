# 049 Heart Rate Notebook Revision Report

## Files changed

- `docs/notebooks/heart-rate-analysis.ipynb` (revised)
- `docs/notebooks/heart-rate-batch-analysis.ipynb` (new)
- `src/acqstore/acq_image/analysis/heart_rate_analysis/plotting/plotly_plots.py` (shared frequency x-axis in summary plot)
- `tests/acqstore/test_heart_rate_plotting.py` (test for shared x-axis)
- `mkdocs.yml` (batch notebook nav entry)
- `docs/scientists/notebooks.md` (batch notebook index link)

## Summary of implementation

Revised the heart rate analysis notebook per user feedback:

1. Added CloudScope GUI / batch-comparison narrative; removed CI/run-local note from notebook body.
2. Removed long registration markdown; kept inline import comments only.
3. Did **not** change any `__init__.py` re-exports (deferred to separate task).
4. Moved synthetic-only core imports into the synthetic demo cell.
5. Removed `AnalysisKey` and `PathKind` from notebook code; use `get_or_create(...).key` and folder auto-detection on `AcqImageList`.
6. Kept `DiameterAnalysis` import with comment explaining sidecar all-or-nothing loading requirement.
7. Added Radon velocity parameter display and velocity-vs-time Plotly plot before heart rate.
8. Kept accept/reject ROI strategy (ROI 3 / ROI 1) as requested.
9. Updated `plot_summary_plotly` so Welch and Lomb panels share the same frequency x-axis (`matches="x2"`).
10. Added companion batch notebook: fixed params, iterate `AcqImageList`, results DataFrame, Lomb-vs-Welch scatter (no sidecar save).

Notebook execution for MkDocs remains manual (`execute: false`); user runs all cells and saves outputs.

## Tests added or modified

- `tests/acqstore/test_heart_rate_plotting.py` — added `test_plotly_summary_shares_frequency_xaxis`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_heart_rate_plotting.py -q
uv run python scripts/_verify_hr_notebook.py
```

## Test results

- 8 passed (heart rate plotting tests)
- Notebook logic verification: ROI 3 accept, ROI 1 reject, batch 8 rows, shared x-axis OK

## Concerns or follow-ups

- User should re-run all cells in both notebooks and save so MkDocs shows updated outputs (including shared x-axis plots).
- `__init__.py` analysis re-exports deferred to separate task.
- Future: run velocity fresh in notebook (point 8) instead of relying on saved sample velocity.
- Future: apply same notebook style to velocity and diameter notebooks.
