# Ticket 012 — Server contract and AcqStore adapter boundary

## Goal

Keep API v2 production work focused by separating server-owned contract tests
from AcqStore-owned format-decoding tests.

## Scope

- replace most direct file-decoding tests in `test_open_service.py` with a
  deterministic fake of the exact public `AcqImage` surface used by the server;
- retain two tiny generated-TIFF smoke tests that detect public AcqStore API
  drift;
- document the testing boundary for future contributors and LLMs.

## Non-goals

- no new endpoints;
- no new service abstraction;
- no proprietary or representative microscope fixtures;
- no format-specific correctness assertions;
- no production behavior changes;
- no changes outside `src/acqstore_server/`, `tests/acqstore_server/`, and
  `docs-dev/acqstore_server/`.

## Rationale

The server owns HTTP adaptation, sessions, binary encoding, validation, and
client discoverability. AcqStore owns file-format decoding. Keeping these
responsibilities separate makes failures easier to interpret and avoids
retesting AcqStore inside the server project.
