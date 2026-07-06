# 043 — Schema to markdown docs generator

## Summary

Added a backend helper that renders markdown documentation tables from AcqStore
schemas, plus a runnable script that prints tables for the four requested
schemas. Also repointed developer-doc cross-references from the old `docs/`
location to the new `docs-dev/` location (the live MkDocs site keeps `docs/`).

The helper unifies the two AcqStore schema families:

- `acqstore.schema.FieldSchema` (experiment metadata, image header metadata).
- `acqstore.acq_image.analysis.model.DetectionParamSchema` (velocity and
  diameter detection parameters).

Both expose `name`, `display_name`, `value_type`, `default`, `description`,
`choices`, `unit`, and `editable`, which allows a single normalization pass.

## Files changed

Added:

- `src/acqstore/schema_docs.py` — `generate_markdown_table(fields, *, title=None, print_markdown=True) -> str`.
- `scripts/acqstore/try_schema_docs.py` — prints all four tables.
- `tests/acqstore/test_schema_docs.py` — unit tests.
- `docs-dev/codex_tickets/043_schema_markdown_docs_report.md` — this report.

Modified (developer-doc reference cleanup `docs/` → `docs-dev/`):

- `AGENTS.md` — ticket report path, structure block; removed the
  `code_review.md` references (file does not exist under `docs-dev/`).
- `src/acqstore/README.md` — documentation index links.
- `src/nicewidgets/image_toolbar_widget/README.md` — packages README link.
- `src/acqstore/acq_image/analysis/diameter_analysis/diameter_core.py` — axis
  convention docstring reference.
- `docs-dev/cloudscope_project_rules.md` — repo layout block (adds `docs-dev/`).
- `docs-dev/cloudscope_architecture.md` — project rules reference.
- `docs-dev/cursor_understanding.md` — multiple dev-doc references.
- `docs-dev/cloudscope_diameter_glue.md` — kymograph axes reference.
- `docs-dev/acqstore_kymograph_axes.md` — diameter glue reference.
- `docs-dev/packages/README.md` — ticket reports reference.

Intentionally left unchanged:

- `mkdocs.yml` (`custom_dir: docs/assets/overrides`) and
  `scripts/apply_replacements_docs.sh` — these correctly target the live MkDocs
  `docs/` folder.
- "Keep long tutorials in `docs/`" guidance — `docs/` is the MkDocs folder.
- Historical ticket reports under `docs-dev/codex_tickets/` — preserved as a
  record.

## Behavior

- Table always includes core columns: `name`, `type`, `default`, `description`.
- Optional columns are added only when at least one field provides an
  informative value: `display_name`, `unit`, `choices`, `editable`, `required`,
  `group` (FieldSchema), `methods` (DetectionParamSchema).
- Defaults are formatted: `None` → `None`, strings quoted, enum members rendered
  via their `value`.
- Empty input raises `ValueError` (fail-fast).
- Uses `pandas.DataFrame.to_markdown`, which requires `tabulate`.

## Dependency note

`tabulate` is required by `df.to_markdown()` and is currently present in the dev
environment but is **not** declared in `pyproject.toml`. Declaring it (per
maintainer preference, in a dependency group) is left to the maintainer.

## Tests

Added `tests/acqstore/test_schema_docs.py`:

- Empty input raises.
- Core columns always present.
- FieldSchema values rendered (type, `None` default, group, description).
- String default is quoted.
- Optional column omitted when not informative.
- DetectionParamSchema `choices` and `methods` columns appear and format.
- All four real schemas generate non-empty tables containing every field name.

### Commands run

```bash
uv run pytest tests/acqstore/test_schema_docs.py -q
uv run python scripts/acqstore/try_schema_docs.py
```

### Results

- `7 passed`.
- Script printed all four markdown tables successfully.

## Follow-up: save-to-file + timestamp/version

`scripts/acqstore/try_schema_docs.py` was expanded to also write one standalone
markdown page per schema under `docs/schemas/` (overwriting existing files):

- `experimental_metadata.md` ← `EXPERIMENT_METADATA_SCHEMA`
- `header_metadata.md` ← `IMAGE_HEADER_METADATA_SCHEMA`
- `velocity_detection_parameters.md` ← `RadonVelocityAnalysis.get_detection_schema()`
- `diameter_detection_parameters.md` ← `DiameterAnalysis.get_detection_schema()`

Each page has a `# Title` heading, the markdown table, and an italic footer:
`*Generated on YYMMDD HH:MM:SS · cloudscope vX.Y.Z*`. The timestamp uses local
time without timezone; the version is read from `pyproject.toml` via stdlib
`tomllib` (no new dependency). Tables are also still printed to the console.
`src/acqstore/schema_docs.py` and `pyproject.toml` were not changed. The four
schema pages are not yet wired into `mkdocs.yml` nav (left to the maintainer).

## Concerns / follow-ups

- `tabulate` should be declared as a dependency (maintainer to choose group).
- `AGENTS.md` previously referenced `docs/code_review.md`, which does not exist
  under `docs-dev/`; those references were removed rather than repointed.
- `src/acqstore/README.md` "Architecture" link was remapped to
  `docs-dev/cloudscope_architecture.md` (filename differs from old
  `docs/architecture.md`).
