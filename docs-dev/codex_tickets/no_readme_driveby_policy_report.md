# No drive-by README.md updates

## Files changed

- `AGENTS.md` — **`README.md` (STRICT)** section; boundary rule bullet
- `.cursor/rules/no-readme-driveby.mdc` — new always-applied Cursor rule
- `docs-dev/cloudscope_project_rules.md` — Documentation Rules subsection

## Summary of implementation

Documented that repo root `README.md` is not updated during normal code/test/docs
tickets. README is rewritten only in an explicit dedicated pass after API and
`src/` work is finalized. Agents should use docstrings, `docs/`, and `docs-dev/`
instead.

## Tests added or modified

None.

## Exact test commands run

None.

## Test results

N/A

## Concerns or follow-ups

None.
