# 053 — Detection schema DataFrame API and schema docs script

## Summary

Added `BaseAnalysis.get_detection_schema_dataframe()` as the public scripting
API for describing an analysis type's detection-parameter schema as a pandas
DataFrame indexed by parameter name. The DataFrame is built directly from
`DetectionParamSchema` fields with no dependency on a separate schema-docs
module.

Replaced the old `schema_docs.py` / `generate_markdown_table()` machinery with
a simple dev-only script `scripts/docs/generate_schema.py` that writes MkDocs
schema pages using `DataFrame.to_markdown()`. Analysis schemas use
`get_detection_schema_dataframe()`; metadata schemas use a small local helper
in the script.

Updated `docs/notebooks/velocity-analysis.ipynb` to use the new one-line API.

## Files changed

Added:

- `scripts/docs/generate_schema.py` — dev helper to generate `docs/schemas/*.md`.
- `docs-dev/codex_tickets/053_schema_dataframe_api_report.md` — this report.

Modified:

- `src/acqstore/acq_image/analysis/model.py` — added
  `get_detection_schema_dataframe()`.
- `tests/acqstore/test_analysis_detection_schema.py` — added DataFrame tests.
- `docs/notebooks/velocity-analysis.ipynb` — simplified schema display cell.

Removed:

- `src/acqstore/schema_docs.py`
- `tests/acqstore/test_schema_docs.py`
- `scripts/acqstore/try_schema_docs.py`

## Tests added or modified

Added to `tests/acqstore/test_analysis_detection_schema.py`:

- `get_detection_schema_dataframe()` returns indexed DataFrame for Radon velocity
- empty detection schema returns empty DataFrame with standard columns

Removed `tests/acqstore/test_schema_docs.py` (superseded by the new approach).

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_analysis_detection_schema.py -q
uv run python scripts/docs/generate_schema.py
```

## Test results

- `24 passed` in 0.53s (includes 2 DataFrame tests from ticket 053 in the same run)
- `uv run pytest tests/acqstore/test_analysis_detection_schema.py -q` — 12 passed
- `uv run python scripts/docs/generate_schema.py` — exit 0; wrote all schema pages under `docs/schemas/`

## Concerns or follow-ups

- `scripts/docs/generate_schema.py` now also writes Event and Heart Rate schema
  pages in addition to the four pages produced by the old script.
- Markdown generation requires `tabulate` for `DataFrame.to_markdown()` (same as
  before).
- `metadata.generate_schema_docs()` in `metadata.py` was not changed.
