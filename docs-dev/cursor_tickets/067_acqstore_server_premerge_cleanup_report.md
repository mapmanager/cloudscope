# 067 — AcqStore Server pre-merge cleanup

## Goal

Prepare `feature/acqstore_server` for a local merge into `main` by fixing
non-additive mistakes and relocating example HTML clients out of a top-level
`clients/` tree.

## Files changed

- `README.md` — restored from `main` (CloudScope public README; undoes accidental AcqStore stub)
- `scripts/make-src-dev.sh` — fix concatenated `workflowsREADME.md` typo; keep intentional `uv.lock` + `.github/workflows` zip includes
- `clients/neuronal_calcium_linescan/*.html` → `scripts/acqstore_server/clients/neuronal_calcium_linescan/` (`git mv`)
- `docs-dev/acqstore_server/v1/html_integration.md` — live path updates
- `docs-dev/acqstore_server/v1/llm_agent_guide.md` — live path updates
- `docs-dev/acqstore_server/v1/roadmap.md` — live path updates
- `docs-dev/cursor_tickets/067_acqstore_server_premerge_cleanup_report.md` — this report

## Summary of implementation

1. Restored repo-root `README.md` from `main` so a merge cannot overwrite the
   CloudScope public overview with an AcqStore Server stub.
2. Validated `scripts/make-src-dev.sh` zip argument list:
   `… pyproject.toml uv.lock .github/workflows README.md`.
3. Moved tracked calcium HTML forks from top-level `clients/` to
   `scripts/acqstore_server/clients/neuronal_calcium_linescan/` (peer to
   `demo_cursor_client*.html`). Parent dir must exist before `git mv`.
4. Updated live v1 docs paths only. Historical `docs-dev/cursor_tickets/04x–06x`
   paths left unchanged.
5. Left `scripts/apply_replacements_docs.sh` deleted (intentional).

## Tests added or modified

None.

## Exact test commands run

```bash
# path / zip-arg existence checks (local shell)
test -e src && test -e tests && test -e docs-dev && test -e scripts
test -e pyproject.toml && test -e uv.lock && test -e .github/workflows && test -e README.md
git ls-files 'scripts/acqstore_server/clients/**'
git diff main -- README.md   # expect empty after restore
```

## Test results

- Zip include paths all exist on disk.
- No tracked files remain under top-level `clients/`.
- Working-tree `README.md` matches `main:README.md` blob.

## Concerns or follow-ups

- Merge into `main` is **not** done in this ticket; user will merge locally after review/commit.
- Optional: run `uv run pytest tests/acqstore_server` before merge.
- Do not reintroduce top-level `clients/` on `main`.
