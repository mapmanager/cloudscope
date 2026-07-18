# 070 — Prepare CloudScope v0.2.0 version bump

## Goal

Bump release metadata to `0.2.0` after CHANGELOG / MkDocs / README prep
(tickets 068–069), ready for user commit + tag.

## Files changed

- `pyproject.toml` — `version = "0.2.0"`
- `CHANGELOG.md` — `[0.2.0] - 2026-07-18` (tag-day date)
- `uv.lock` — synced package version `cloudscope` `0.1.3` → `0.2.0`
- `docs-dev/cursor_tickets/070_prepare_v0_2_0_version_bump_report.md` — this report

## Summary of implementation

1. Set project version to `0.2.0`.
2. Filled CHANGELOG date placeholder with `2026-07-18`.
3. Ran `uv lock` to update the locked cloudscope version.

No git tag and no commit in this ticket (user must request).

## Tests added or modified

None.

## Exact test commands run

```bash
uv lock
uv run python scripts/check_release.py --ci v0.2.0
```

## Test results

```text
OK: tag 'v0.2.0' matches pyproject.toml version '0.2.0'.
OK: CHANGELOG.md contains a section for [0.2.0].
OK: release metadata checks passed.
```

(`--ci` used because the working tree is dirty until the user commits.)

## Concerns or follow-ups

User next steps (when ready):

1. Commit version bump files (and this report).
2. Working tree clean on `main`.
3. `uv run python scripts/check_release.py v0.2.0` (full checks).
4. `git tag v0.2.0 && git push origin v0.2.0` (and push commits as needed).

Do **not** push or tag without an explicit user request.
