# Packages (`acqstore` and `nicewidgets`)

This repository keeps **backend acquisition logic** and **reusable NiceGUI widgets** separate from the CloudScope app (`src/cloudscope/`).

## `src/acqstore/` — acquisition store

- **Role:** Data models, file loaders, ROI geometry, metadata, and list-level APIs. No NiceGUI.
- **Entry:** [`src/acqstore/README.md`](../../src/acqstore/README.md) (overview and import hints).
- **Further reading:** [`../acqstore/schemas.md`](../acqstore/schemas.md), ticket reports under [`../tickets/reports/`](../tickets/reports/) (e.g. schema and import-path work).

## `src/nicewidgets/` — reusable NiceGUI widgets

- **Role:** UI components usable from CloudScope or other apps. **Must not** import `cloudscope`.
- **Pattern:** Import from concrete submodules (no package-level re-exports), e.g. `from nicewidgets.table_widget.table_widget import TableWidget`.
- **Documented widgets:**
  - [`../../src/nicewidgets/table_widget/README.md`](../../src/nicewidgets/table_widget/README.md) — AG Grid table wrapper.
  - [`../../src/nicewidgets/image_toolbar_widget/README.md`](../../src/nicewidgets/image_toolbar_widget/README.md) — image file label, channel/ROI selects, ROI intent toolbar.

## CloudScope app

Application orchestration, contracts, and GUI live under `src/cloudscope/`. See [`../architecture.md`](../architecture.md) and `AGENTS.md` at the repo root for boundaries.

## Pointing an LLM at this tree

1. Read this file and the two package READMEs linked above.
2. For behavior changes, cross-check `docs/tickets/reports/` for the relevant ticket report.
3. Run tests with `uv run pytest` from the repo root.
