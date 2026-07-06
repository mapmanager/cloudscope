# Ticket 024: AcqStore tree-row API

## Files changed

- `src/acqstore/acq_image/tree_rows.py`
- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/acq_image_list.py`
- `tests/acqstore/test_acq_image_tree_rows.py`
- `docs/codex_tickets/024_acqstore_tree_row_api_report.md`

## Summary of implementation

Added an AcqStore-owned tree-row contract for the future CloudScope
`TreeWidget` file-list swap. The change is additive:

- Added `tree_rows.py` constants for tree row id, path, row type, and analysis
  identity fields.
- Added `build_analysis_tree_row_id(...)` for stable child analysis row ids.
- Added `AcqImage.get_tree_rows()` returning the file row plus analysis child
  rows.
- Added `AcqImageList.get_tree_rows()` flattening file subtrees in stable
  display order.

No existing AcqStore APIs were removed or changed. Existing schema row APIs
remain unchanged.

## Tests added or modified

- Added `tests/acqstore/test_acq_image_tree_rows.py`
  - verifies parent/child row shape
  - verifies stable/unique analysis row ids
  - verifies list-level flattening preserves display order
  - verifies existing schema-row output is unchanged

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_image_tree_rows.py tests/acqstore/test_acq_image_list.py -q
uv run pytest tests/acqstore/ -q
```

## Test results

- `19 passed in 0.56s`
- `217 passed in 1.81s`

## Concerns or follow-ups

- CloudScope has not been switched from `TableWidget` to `TreeWidget` yet.
- Future CloudScope swap should import the tree-row constants from AcqStore and
  configure `TreeWidget` with those field names.
- `file_list_view` should use `TreeWidget.replace_group_rows(...)` for targeted
  updates so analysis child rows are added/removed with the parent file row.
