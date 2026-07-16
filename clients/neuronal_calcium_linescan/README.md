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
5. Server / agent context: `docs-dev/acqstore_server/llm_agent_guide_v0.md`.

## Run

1. Start server (API-only or desktop):
   ```bash
   uv run python -m acqstore_server
   # or: uv run python -m acqstore_server.desktop
   ```
2. Open `neuronal_calcium_linescan_analyzer_v1_18.html` in a browser (`file://` or any static host).
3. **TIFF path:** use Calcium / Vessels file inputs → **Load channel(s)** (unchanged).
4. **AcqStore path:** set base URL if needed (default `http://127.0.0.1:8767`) → **Load from AcqStore Server** → native OS dialog → calcium (+ vessels) planes + calibration.
5. **Reference overview:** collapsible card between Image Display and Trace Display; filled when open JSON has `reference` (scan path / lineRoi overlay, display-transposed like `/demo/`).
