# 048 Heart Rate Analysis Notebook Report

## Files changed

- `docs/notebooks/heart-rate-analysis.ipynb` (new)
- `mkdocs.yml` (nav entry)
- `docs/scientists/notebooks.md` (index link)

## Summary of implementation

Added a narrative + code + Plotly notebook for heart rate analysis under `docs/notebooks/heart-rate-analysis.ipynb`. The notebook:

1. Loads `demo-small` via `ensure_sample` and imports analysis classes before sidecar hydration.
2. Reuses saved `radon_velocity` analyses (with optional re-run fallback) for channel 0 ROIs.
3. Displays the full heart rate detection schema and explains key parameters.
4. Runs heart rate with user-chosen parameters on ROI 3 (accept) and ROI 1 (reject) on `20251030_A106_0002.oir`.
5. Explains Lomb-vs-Welch agreement as the accept/reject QC mechanism.
6. Renders Plotly summary and segment-series diagnostics via `acqstore` plotting helpers.
7. Includes a synthetic 360 bpm ground-truth sanity check.

Registered the notebook in MkDocs nav and the scientist notebooks index page.

## Tests added or modified

None (documentation notebook only; not executed in CI per existing mkdocs-jupyter config).

## Exact test commands run

```bash
uv run python scripts/_verify_hr_notebook.py
```

(Ad-hoc script mirroring notebook cells; removed after verification.)

## Test results

- ROI 3 accept case: `status=ok`, lomb≈440.1 bpm, welch≈419.3 bpm, `agree_ok=True`
- ROI 1 reject case: `status=method_disagree`, lomb≈308.3 bpm, welch≈389.4 bpm, `agree_ok=False`
- Synthetic 360 bpm: lomb≈359.8 bpm, welch≈360.0 bpm
- Plotly figures created without error

## Concerns or follow-ups

- Full `jupyter nbconvert --execute` was not run in this session; local execution recommended after `uv sync --group docs`.
- Existing velocity/diameter notebooks remain stubs; could be expanded similarly later.
- Notebook uses saved velocity from demo-small; re-running Radon in-notebook is supported but slow.
