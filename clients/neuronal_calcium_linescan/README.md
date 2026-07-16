# Neuronal calcium linescan HTML (in-repo fork)

Working copy of the ~5k-line analyzer used with **AcqStore Server**.

## Provenance

- File: `neuronal_calcium_linescan_analyzer_v1_18.html`
- Imported from the Desktop “Neuronal Calcium Linescan Analyzer” tree (v1.18).
- This is our fork for an **additive** “Load from AcqStore Server” path. Keep the existing TIFF / file-input load.

## Edit rules

1. **Do not delete** upstream code — comment it out and note why + ticket id.
2. Wrap **new** blocks in HTML comments:
   `<!-- ACQSTORE: begin NNN short-title -->` … `<!-- ACQSTORE: end NNN short-title -->`
3. Every HTML change gets a report under `docs-dev/cursor_tickets/`.
4. Implement against `docs-dev/acqstore_server/html_integration_v0.md` and
   `reference_api_v0.md` — do not invent API fields.

## Run

1. Start server: `uv run python -m acqstore_server`
2. Open this HTML in a browser (`file://` or any static host).
3. Use existing TIFF load and/or (when implemented) server pick-and-open.
