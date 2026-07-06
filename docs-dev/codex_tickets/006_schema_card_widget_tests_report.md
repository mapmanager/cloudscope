# Ticket 006 — SchemaCardWidget headless tests

## Files changed

- `tests/cloudscope/test_schema_card_widget.py` — new file with 12 tests
- `docs/codex_tickets/006_schema_card_widget_tests_report.md` (this report)

## Summary of implementation

`SchemaCardWidget` previously had 0% coverage on its public pure helpers and
`get_patch` because there were no tests for it. The class exposes seam-friendly
helpers (`_label_for_field`, `_stringify_readonly`, `_has_editable_fields`,
`_group_visible_fields`, `get_patch`, `_apply`, `update_values`) that do not
need a NiceGUI slot.

New tests cover:

- `_label_for_field`: appends `(unit)` when set, omits when missing.
- `_stringify_readonly`: maps None to empty string, str()'s other values.
- `_has_editable_fields`: False when no visible+editable fields, True
  otherwise.
- `_group_visible_fields`: preserves first-appearance group order, includes
  `None` group, and skips invisible fields.
- `get_patch`: returns only visible+editable fields with a registered control
  (skips readonly, invisible, and missing-control fields).
- `_apply`: invokes the `on_apply` callback with `get_patch()`; no-op when
  no callback is configured.
- `update_values`: updates matching control values + calls `.update()`,
  ignores keys without a control.

## Tests added or modified

12 tests in the new file `tests/cloudscope/test_schema_card_widget.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_schema_card_widget.py -q
uv run pytest tests/cloudscope/test_schema_card_widget.py --cov=cloudscope.views.metadata_widget.schema_card_widget --cov-report=term-missing -q
```

## Test results

- 12 passed
- `schema_card_widget.py` coverage: **16% → 55%** (105 statements, 47 missed)
- Remaining missed lines are the NiceGUI `build()` path (35-39, 42-54)
  and `_build_field` for each ValueType (108-152). These call
  `ui.card()`, `ui.label`, `ui.checkbox`, `ui.number`, `ui.select`,
  `ui.input` which require an active NiceGUI slot/client.

## Concerns or follow-ups

- `_build_field` per-`ValueType` branches could be covered by a test-client
  smoke test that constructs the card inside a `ui.column()`. Out of scope
  for this ticket.
