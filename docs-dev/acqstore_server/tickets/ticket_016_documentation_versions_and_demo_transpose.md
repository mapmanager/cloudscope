# Ticket 016 — Documentation versions and demo transpose

## Goal

Organize AcqStore Server documentation by API version and make the maintained v2 demo explicitly transpose planes immediately before display.

## Scope

- `docs-dev/acqstore_server/`
- `src/acqstore_server/static/demo/v2/index.html`
- `tests/acqstore_server/v2/test_demo.py`

No API endpoint, v1 runtime, AcqStore, external client, or packaging behavior changes.

## Implementation

- Replaced the root README with a versioned landing page.
- Separated JavaScript/end-user instructions from Python/release developer instructions.
- Documented that the packaged macOS app is supplied by AcqStore Server developers and is available on request.
- Copied legacy v1 documents into `docs-dev/acqstore_server/v1/` with stable names.
- Added a v1 compatibility README.
- Removed the unnecessary biological-role statement from the v2 README.
- Removed the old orientation paragraph from the v2 demo page.
- Added `transposePlane()` and call it immediately before drawing every primary or reference plane.
- Added regression assertions protecting the explicit transpose call.

## Required cleanup after applying replacements

Because the repository replacement helper copies files but does not delete old paths, remove these legacy root copies after applying this ticket:

```bash
rm docs-dev/acqstore_server/entry_point_and_packaging.md \
   docs-dev/acqstore_server/html_integration_v0.md \
   docs-dev/acqstore_server/llm_agent_guide_v0.md \
   docs-dev/acqstore_server/reference_api_v0.md \
   docs-dev/acqstore_server/roadmap.md
```

Their full contents are preserved under `docs-dev/acqstore_server/v1/`.

## Validation

- v2 demo tests verify the explicit transpose helper and call site.
- v1 routes and clients are unchanged.
- Python compilation and focused tests should pass.

## Files changed

- `docs-dev/acqstore_server/README.md`
- `docs-dev/acqstore_server/v1/*.md`
- `docs-dev/acqstore_server/v2/README.md`
- `docs-dev/acqstore_server/v2/demo.md`
- `src/acqstore_server/static/demo/v2/index.html`
- `tests/acqstore_server/v2/test_demo.py`

## Next steps

Build the authoritative v2 JavaScript client guide with one complete copyable workflow from health check through session cleanup.
