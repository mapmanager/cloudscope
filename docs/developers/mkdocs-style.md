# MkDocs style guide (CloudScope)

Conventions for authoring CloudScope documentation with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).
Use the pattern names below when discussing doc changes in issues and PRs.

Site config: `mkdocs.yml`. Source pages: `docs/`.

---

## Pattern names (quick reference)

| Name | When to use | Markdown |
|---|---|---|
| **Inline Material icon** | Match a GUI Quasar/Material icon in prose (history menu, etc.) | `:material-menu:{ .middle }` |
| **Tip block** | Optional shortcut or friendly suggestion | `!!! tip "Title"` |
| **Info block** | Neutral context, metadata, “validated on” notes | `!!! info "Title"` |
| **Warning block** | Required step; skipping it causes failure or bad UX | `!!! warning "Title"` |
| **Platform tabs** | Same topic, different steps per OS (Windows / macOS) | `=== "Windows"` / `=== "macOS"` |
| **Recipe hub** | Index page linking to focused workflow pages | `docs/users/recipes/index.md` |
| **Audience scope** | End User vs Data Scientist vs Developer tone and detail | [Audience and scope](#audience-and-scope) |
| **Nested recipe nav** | Group dependent analyses under a nav section | `Analyses from velocity` in `mkdocs.yml` |
| **Home cards** | Landing-page navigation tiles | `<div class="grid cards" markdown>` |

---

## Admonitions (alert blocks)

Material admonitions render as colored callout boxes. CloudScope uses a small, consistent set:

### Tip block — optional, helpful

Use for “you might prefer this” guidance that is not required.

```markdown
!!! tip "Try CloudScope first"
    You can use the [web application](https://cloudscope.mapmanager.net) without installing.
```

### Info block — context only

Use for provenance, version notes, “validated on” footers, and non-actionable detail.

```markdown
!!! info "Validated on"
    macOS Tahoe 26.2, Apple Silicon.
```

### Warning block — required or failure-prone

Use when the reader **must** do something, or when skipping a step commonly breaks the workflow.
Prefer a short **title** that states the action (“Unblock before extracting”), not just “Warning”.

```markdown
!!! warning "Unblock before extracting"
    Windows marks downloaded files with a security zone flag. If you skip this step,
    CloudScope may fail to start after extraction.

    1. Right-click the ZIP file.
    2. Select **Properties**.
    ...
```

**Do not** use warning blocks for general background; reserve them for steps with real consequences.

Reference: [Material admonitions](https://squidfunk.github.io/mkdocs-material/reference/admonitions/).

---

## Platform tabs

Use **platform tabs** when one page covers the same workflow on multiple platforms (install, verify checksum, CLI examples).

### Rules

1. **One page, shared intro** — put common context (download URL, version naming) above the tabs.
2. **Tab labels** — use `Windows` and `macOS` consistently (same spelling and casing everywhere on the site).
3. **Linked tabs** — `content.tabs.link` is enabled in `mkdocs.yml`; choosing Windows in one tab group selects Windows in other groups on the same page. Reuse the same labels.
4. **Indentation** — tab body content is indented four spaces under `=== "Label"`.
5. **Code inside tabs** — if a tab contains fenced code blocks, wrap the whole tab in a **four-backtick** outer fence (see Material content tabs docs).

### Minimal example

````markdown
## Download and run

=== "Windows"

    Windows-specific steps here.

=== "macOS"

    macOS-specific steps here.
````

### Admonitions inside tabs

Indent the `!!!` line to match other tab content (four spaces). Indent admonition body content four spaces **relative to** `!!!`:

```markdown
=== "Windows"

    !!! warning "Unblock before extracting"
        Step one.
        Step two.
```

Live example: [Get the desktop app](../users/install.md).

Reference: [Material content tabs](https://squidfunk.github.io/mkdocs-material/reference/content-tabs/).

---

## Other patterns in use

### Home cards

The home page uses Material grid cards for primary CTAs (web app, desktop install, audience guides).
See `docs/index.md`.

### External links

Add `{target="_blank" rel="noopener"}` to links that leave the doc site (GitHub Releases, web app, etc.).

### Inline Material icons

CloudScope uses [Material for MkDocs icon emoji](https://squidfunk.github.io/mkdocs-material/reference/icons-emojis/) syntax. The site enables this via `pymdownx.emoji` with `material.extensions.emoji.to_svg` in `mkdocs.yml` (same mechanism as `:material-web:` on the home page).

Use **in prose only** (not in tables). Add `{ .middle }` so the icon aligns with surrounding text:

```markdown
Open the history menu (:material-menu:{ .middle }) and choose …
```

Icon names use hyphens (`material-menu`, `material-account-tree`). Prefer icons that match the Quasar `icon=` names used in the GUI where a Material equivalent exists.

Reference: live usage in `docs/index.md` (home cards) and `docs/users/gui.md` (history menu).

### Screenshots

Use the project classes for consistent sizing:

```markdown
![Description](../assets/gui/example.png){ .cs-screenshot .cs-screenshot-center width="760" loading=lazy }
```

---

## Local preview

Docs dependencies are in the `docs` uv group:

```bash
uv sync --group docs
uv run mkdocs serve
```

Strict build (CI-equivalent):

```bash
uv run mkdocs build --strict
```

---

## Audience and scope

CloudScope documentation is organized into three audiences. Match the **scope and tone**
of the section you are editing.

### End User (`docs/users/`)

**Reader:** someone using the desktop or browser GUI to load data, run analyses, and
save results. They may not write Python.

| Do | Don't |
|---|---|
| Name GUI controls exactly as shown (**Peak Detect**, **Load CSV**, **Pool Plots**) | Paste Python APIs, module paths, or `acqstore` package names |
| Link to [Using the GUI](../users/gui.md) sections when referring to a control area (for example the [load/save controls](../users/gui.md#top-header-and-loadsave-controls)) | Repeat “uses the same backend” on every page |
| Call the sum-intensity workflow **peak detection** in prose (the left-toolbar label) | Dive into axis remapping, loader internals, or runtime extension sets |
| Explain *what to click* and *what you get* | Document implementation details better suited to Data Scientist or Developer pages |

Explain the **shared backend** at most once per page, and only when it helps the reader
understand reproducibility (for example saved files reload consistently). Prefer linking to
[Reproducibility](../scientists/reproducibility.md) over naming `acqstore` repeatedly.

### Data Scientist (`docs/scientists/`, `docs/notebooks/`)

**Reader:** someone scripting with `AcqImage` / `AcqImageList`, tuning detection
parameters, or running notebooks.

| Do | Don't |
|---|---|
| Document parameters, saved-file layout, and notebook workflows | Duplicate full GUI click-path recipes (link to End User recipes instead) |
| Use module names (`SumIntensityAnalysis`, `ensure_sample`) where they are the API | Assume the reader only wants GUI steps |
| Note when a workflow has **no GUI panel yet** (for example heart rate) | |

The GUI label **Peak Detect** maps to the `SumIntensityAnalysis` backend module — mention
both when the distinction matters.

### Developer (`docs/developers/`, `docs/api/`)

**Reader:** contributor or integrator working in `src/`, CI, packaging, or generated API
reference.

Package names (`acqstore`, `nicewidgets`, `cloudscope`) belong here. Cross-link upward to
user-facing pages when documenting features that also appear in the GUI.

### Site-wide consistency

- **Supported formats:** whenever you list formats, include **Nikon `.nd2`** and split
  **commercial** vs **open** formats when the list is more than a casual mention. Canonical
  detail: [Supported file formats](../users/supported-file-formats.md).
- **Internal links:** prefer relative links to other doc pages; use section anchors
  (`gui.md#top-header-and-loadsave-controls`) when pointing at a specific GUI region.
- **Load/save vs top header:** when referring to loading or saving (Load File/Folder,
  **Load CSV**, the **history menu**, **Save Selected** / **Save All**), call it the
  **load/save controls**. Reserve **top header** for describing the header region itself
  (on `gui.md`) or for the **Pool Plots** button, which lives in the header but is not a
  load/save control.
- **Avoid repetition:** if the home page or End User index already states a fact, later pages
  should link rather than restate it.
- **Naming:** End User docs → **peak detection**; Data Scientist / API → **sum intensity
  analysis** (module name) with a note that the GUI says Peak Detect.

---

## Adding new patterns

Before introducing a new Material feature (e.g. diagrams, annotations, new admonition types):

1. Confirm the extension is listed in `mkdocs.yml` `markdown_extensions` or `theme.features`.
2. Add one canonical example to this guide.
3. Add a row to the quick reference table at the top.
