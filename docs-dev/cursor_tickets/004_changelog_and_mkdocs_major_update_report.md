# 004 — CHANGELOG rewrite and major MkDocs update

## Summary

Two coordinated pieces of work:

1. **CHANGELOG.** Rewrote the `[Unreleased]` section to capture every
   semi-significant change since tag `0.1.3` (2026-06-23), grouped by the three
   CloudScope source packages (`acqstore`, `nicewidgets`, `cloudscope`) plus
   `Desktop app` and `Documentation`, each split into Added / Changed / Fixed.
   Added explicit lines for the registered `diameter-sample-data` and
   `velocity-sample-data` sample datasets.

2. **MkDocs.** Executed the approved four-phase docs update (A→D):
   - **Phase A — accuracy audit.** Fixed stale prose: a dangling reference to a
     non-existent `sum-intensity-algorithm.ipynb`, a stale "load from a local
     folder" line, added a local-data disclaimer to the kymograph notebook, and
     cross-linked blinded mode / randomized sampling from `gui.md` and
     `notebooks.md`. Confirmed heart rate still has no GUI panel (kept the
     "no GUI yet" note) and that no ECharts references remain in doc/notebook
     prose.
   - **Phase B — new content.** Added six new pages and one new notebook (see
     Files changed). Migrated every data notebook off the retired `demo-small`
     sample onto the registered `ensure_sample()` datasets and re-executed them.
     Rewrote the heart-rate notebook's accept/reject narrative to contrast two
     real files from `velocity-sample-data` (the old single-file ROI-3-vs-ROI-1
     contrast no longer exists in the new sample).
   - **Phase C — navigation.** Wired all new pages into `mkdocs.yml` nav
     (End User, Data Scientist, API sections).
   - **Phase D — build.** `mkdocs build --strict` passes cleanly.

## Files changed

### CHANGELOG
- `CHANGELOG.md` — rewrote `[Unreleased]`, grouped by package; sample-data and
  documentation entries.

### New documentation pages
- `docs/users/supported-file-formats.md`
- `docs/users/blinded-mode.md`
- `docs/scientists/heart-rate-analysis.md`
- `docs/api/heart-rate-analysis.md`
- `docs/api/event-analysis.md`
- `docs/api/analysis-pools.md`
- `docs/notebooks/generating-randomized-file-for-analysis.ipynb` (new notebook)

### Edited documentation
- `docs/users/gui.md` — Load CSV + Config rows link blinded mode and randomized
  sampling.
- `docs/scientists/notebooks.md` — added the randomized-subset notebook.
- `mkdocs.yml` — nav entries for all new pages.

### Notebooks migrated to registered samples and re-executed
- `docs/notebooks/load-and-plot-image.ipynb` → `velocity-sample-data`
- `docs/notebooks/velocity-analysis.ipynb` → `velocity-sample-data`
- `docs/notebooks/heart-rate-analysis.ipynb` → `velocity-sample-data`
  (accept file `20251030_A106_0002.oir`, reject file `20250717_A87_0004.oir`)
- `docs/notebooks/heart-rate-batch-analysis.ipynb` → `velocity-sample-data`
- `docs/notebooks/diameter-analysis.ipynb` → `diameter-sample-data`
- `docs/notebooks/sum-intensity-analysis.ipynb` → `diameter-sample-data`
  (removed a hardcoded local Dropbox path)
- `docs/notebooks/kymograph-reference-image.ipynb` — kept local-path-only per
  decision; added a prominent "local data required" disclaimer. Legacy output
  fields (`name`, `metadata`) normalized so the strict build passes.

### Repo hygiene
- `.gitignore` — ignore `.ipynb_checkpoints/`.
- Removed 5 accidentally-committed `docs/notebooks/.ipynb_checkpoints/*` files
  (Jupyter autosave artifacts that still referenced `demo-small`).
- `scripts/_run_notebook.py` — small reusable helper to execute a docs notebook
  in place (tolerant of legacy output formats via `nbformat` normalization).

## Design decisions (confirmed with user)

- Kymograph notebook stays a local-path demo with a disclaimer (not wired to
  `ensure_sample`) because its reference-image / multi-line scan-path examples
  need specific OIR/CZI files not present in the registered sample archives.
- The randomized-subset notebook demonstrates on `velocity-sample-data` but
  documents how to point at an arbitrary user folder and grouping column.
- No dedicated `acqstore.sample_data` API page; sample data is documented inline
  in the notebooks and end-user pages.
- Heart-rate accept/reject teaching point kept, but re-grounded on two real
  files (verified with the notebook's own parameters: accept Δ≈0.2 bpm,
  reject Δ≈151.5 bpm / `method_disagree`).

## Tests / verification commands run

Notebook execution (ephemeral docs env):

```bash
uv run --group docs --with jupyter --with ipykernel --with nbclient \
  python scripts/_run_notebook.py docs/notebooks/<name>.ipynb
```

Ran for: load-and-plot-image, velocity-analysis, diameter-analysis,
heart-rate-analysis, heart-rate-batch-analysis, sum-intensity-analysis,
generating-randomized-file-for-analysis.

Strict docs build:

```bash
uv run --group docs mkdocs build --strict
```

## Results

- All migrated notebooks executed with **exit 0** and no error outputs.
- Randomized notebook produced expected results: 15 files across 3 groups,
  balanced subset of 3×3 = 9 files, 0 load warnings.
- Heart-rate notebook: accept case `status=ok` (Δ0.2 bpm), reject case
  `status=method_disagree` (Δ151.5 bpm), both on channel 0 / ROI 1.
- `mkdocs build --strict` → **"Documentation built in ~5.5 seconds"**, no
  warnings or broken links.

## Concerns / follow-ups

- Cell 25 of `heart-rate-analysis.ipynb` calls `acq.save()`, which writes a
  heart-rate summary into the cached `velocity-sample-data` sidecar JSON. This is
  a benign, re-downloadable local cache side effect; noted in case a future
  ticket wants notebooks to avoid mutating cached samples.
- The randomized notebook's committed output shows an ephemeral `tempfile` path
  (harmless, but a future pass could redact it for cleaner rendering).
- Freshly executed notebooks required legacy output-field normalization
  (`name`/`metadata`) for the strict build; `scripts/_run_notebook.py` handles
  this, but the underlying nbformat/nbconvert strictness is worth keeping in
  mind for future notebook work.
- Repo root `README.md` was updated in a follow-on pass (explicit user request) to
  reflect the MkDocs changes: named sample datasets, blinded/randomized workflow,
  expanded analyses, and documentation nav highlights.

## Follow-up refinement round (site-wide consistency)

A second review pass applied user-requested consistency edits across the site:

- **"Peak detection" naming.** End-user prose now calls the sum-intensity
  workflow **peak detection** (the left-toolbar label): `index.md`, `users/index.md`,
  `users/gui.md`, `users/pool-plots.md`, `users/saved-files.md`,
  `users/recipes/index.md`, and `users/recipes/sum-intensity-analysis.md`
  (retitled to "Peak detection"). Literal GUI/file strings kept:
  `Run Sum Intensity Analysis` button, `sum_intensity.csv` filename, and the
  Data-Scientist page title `Sum Intensity Analysis` (module name).
- **Reduced `acqstore` in end-user docs.** All `acqstore` mentions removed from
  `docs/users/**` (verified: 0 remaining). The "same backend" point is now made
  once, framed around reproducibility, rather than repeated per page.
- **Landing page.** Removed the redundant "same `acqstore` backend is used by…"
  line; added inline links to velocity/diameter/peak-detection recipes, the GUI
  guide, and the top-header anchor; split supported formats into **commercial**
  (added Nikon `.nd2`) vs **open** groups.
- **`users/index.md`.** Removed "CloudScope can load and visualize a range of
  image formats" and the browser-vs-desktop `acqstore` sentence; formats split
  commercial/open with `.nd2`.
- **Nikon `.nd2` site-wide.** Added to every supported-format list
  (`index.md`, `users/index.md`, `users/supported-file-formats.md`,
  `developers/index.md`, `developers/release-and-deployment.md`) and to recipe
  "Before you start" format lists.
- **`users/supported-file-formats.md`.** Removed the code-API reference
  (`get_supported_import_extensions()` / runtime restriction) and the
  `(Y, X)` line-scan-orientation caveat (developer detail, not end-user);
  removed `ensure_sample(...)` from the sample-data section; linked the
  top-header history-menu anchor.
- **Internal anchor links.** Sample-data / Load-CSV mentions now link
  `gui.md#top-header-and-loadsave-controls` (`users/index.md`,
  `users/blinded-mode.md`, `users/supported-file-formats.md`).
- **Diameter notebook.** Now loads `220110n_0003.tif`, channel 0, ROI 1 and was
  re-executed (threshold_width: mean 67.98 µm, CV 0.063; 0 error outputs).
- **Style guide.** Added an **Audience and scope** section to
  `developers/mkdocs-style.md` (End User / Data Scientist / Developer do-and-don't
  tables, site-wide consistency rules for formats, links, repetition, and the
  peak-detection vs sum-intensity naming convention), plus a quick-reference row.

Re-verified: `uv run --group docs mkdocs build --strict` → "Documentation built"
with **0 warnings** after fixing two relative-link paths in the style guide.
```
