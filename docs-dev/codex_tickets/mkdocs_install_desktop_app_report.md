# MkDocs desktop install guide and release checksums

## Files changed

- `mkdocs.yml` — added `pymdownx.tabbed`, `content.tabs.link`, install nav entry
- `docs/users/install.md` — new tabbed Windows/macOS install guide
- `docs/index.md` — desktop download card links to install guide
- `docs/users/index.md` — install section and nav cross-links
- `docs/users/recipes.md` — link fresh-install check to install guide
- `docs/developers/release-and-deployment.md` — artifact naming and checksum notes
- `.github/workflows/build-windows.yml` — SHA-256 generation and upload
- `.github/workflows/build-macos.yml` — upload `.zip.sha256` artifacts
- `packaging/macos/make_release_zip.sh` — `v` prefix in zip basename, SHA-256 sidecar
- `packaging/macos/release_pipeline.sh` — aligned artifact paths and checksum upload

## Summary of implementation

Added a single End User install page with Material content tabs for Windows and macOS
download/run instructions, including optional SHA-256 verification, platform-specific
troubleshooting (Windows), and validated-on notes (Windows 11; macOS Tahoe 26.2 Apple Silicon).

Aligned macOS release zip naming with Windows (`CloudScope-vX.Y.Z-macos.zip`). Both desktop
workflows now publish matching `.zip.sha256` checksum files to GitHub Releases and CI artifacts.

## Tests added or modified

None. Documentation and CI packaging changes only.

## Exact test commands run

```bash
uv run mkdocs build --strict
```

## Test results

`uv run mkdocs build --strict` — **passed** (exit 0, site built in ~5.7s).

## Concerns or follow-ups

- Existing GitHub Release v0.1.3 macOS asset is named `CloudScope-0.1.3-macos.zip` (no `v`);
  the new naming applies from the next tagged release onward.
- Checksum sidecars are not published for v0.1.3; docs describe the pattern for future releases.
- Consider `uv run mkdocs serve` for manual tab UX review in a browser before the next docs deploy.
