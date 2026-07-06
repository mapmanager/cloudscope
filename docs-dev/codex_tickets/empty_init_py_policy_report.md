# Empty __init__.py policy

## Files changed

- `AGENTS.md` — replaced soft “minimal” wording with **`__init__.py` (STRICT)** section and frozen allowlist
- `.cursor/rules/empty-init-py.mdc` — new always-applied Cursor rule with wrong/right examples

## Summary of implementation

Documented that new or updated `__init__.py` files must be empty by default, with
a frozen allowlist of five curated public API surfaces (including
`acqstore/acq_image/__init__.py` for `AcqImage` / `AcqImageList`). Agents must
not modify allowlisted files or add docstring-only inits without an explicit
ticket.

## Tests added or modified

None.

## Exact test commands run

None (documentation and Cursor rules only).

## Test results

N/A

## Concerns or follow-ups

- Existing docstring-only `__init__.py` files are grandfathered until touched;
  optional cleanup ticket could strip them to empty.
- Optional future: pre-commit check with allowlist for empty inits.
