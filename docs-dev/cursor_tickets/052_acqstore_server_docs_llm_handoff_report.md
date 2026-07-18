# 052 — AcqStore Server docs / LLM handoff refresh

## Files changed

- `docs-dev/acqstore_server/llm_agent_guide_v0.md` — **new** preferred agent entry
- `docs-dev/acqstore_server/README.md` — index points at agent guide; client status
- `docs-dev/acqstore_server/roadmap.md` — 049–052 done; remaining open items
- `docs-dev/acqstore_server/html_integration_v0.md` — health fields, load_timeout,
  deleted routes, fork status, reference step no longer “optional only”
- `docs-dev/acqstore_server/reference_api_v0.md` — fork note, dx/dy, deleted URLs
- `docs-dev/acqstore_server/entry_point_and_packaging.md` — API vs native reality
- `clients/neuronal_calcium_linescan/README.md` — link agent guide
- `docs-dev/cursor_tickets/052_acqstore_server_docs_llm_handoff_report.md`

## Summary

Tightened docs so another LLM can start from `llm_agent_guide_v0.md`: product
boundaries, run modes, API map, HTML fork status, ticket index, and **v1
remaining** checklist (rebuild `.app`, port-busy UX, calibration investigate,
Windows later).

No production code changes.

## Tests

None (docs only).

## Test results

N/A

## Concerns / follow-ups

See agent guide “v1 remaining” table — next engineering if shipping the `.app`
is a rebuild/notarize with 048–051 included.
