# Ticket 021 — Cursor onboarding repair and reference hierarchy

## Goal

Apply the findings from the independent Cursor client test and prepare the documentation for a second Milestone 2 attempt.

## Changes

- Rewrites `docs-dev/acqstore_server/README.md` as a short landing page.
- Rewrites `docs-dev/acqstore_server/client-roadmap.md` as a self-sufficient first-client workflow.
- Moves active detailed API v2 documents to `docs-dev/acqstore_server/reference/`.
- Rewrites `reference/README.md` as a lookup-document index.
- Updates the archived v1 landing-page pointer.
- Updates documentation contract tests for the new hierarchy and onboarding requirements.

## Important cleanup after applying replacements

The replacement merge script cannot delete the old directory. After applying this ticket, remove the obsolete duplicate v2 documentation:

```bash
rm -rf docs-dev/acqstore_server/v2
```

Do not remove `src/acqstore_server/v2/` or `tests/acqstore_server/v2/`.

## Resulting documentation tree

```text
docs-dev/acqstore_server/
├── README.md
├── client-roadmap.md
├── reference/
│   ├── README.md
│   ├── api.md
│   ├── architecture.md
│   ├── client-handoff.md
│   ├── demo.md
│   ├── errors.md
│   ├── format-validation.md
│   ├── javascript-client.md
│   ├── python-client.md
│   ├── representative-format-testing.md
│   └── testing.md
├── tickets/
└── v1/
```

## Validation

```bash
uv run pytest tests/acqstore_server/v2/test_documentation_contract.py
uv run pytest tests/acqstore_server
```

## Milestone 2 retry

Give Cursor the root `README.md`, `client-roadmap.md`, and the source tree again. The roadmap now includes the base URL, start command, open bodies, response fields, relative binary URL rule, byte validation, portable Float32 decoding, optional transpose semantics, cancellation, TTL, demo URL, and explicit session deletion.
