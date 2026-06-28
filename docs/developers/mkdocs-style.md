# MkDocs style guide (CloudScope)

Conventions for authoring CloudScope documentation with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).
Use the pattern names below when discussing doc changes in issues and PRs.

Site config: `mkdocs.yml`. Source pages: `docs/`.

---

## Pattern names (quick reference)

| Name | When to use | Markdown |
|---|---|---|
| **Tip block** | Optional shortcut or friendly suggestion | `!!! tip "Title"` |
| **Info block** | Neutral context, metadata, “validated on” notes | `!!! info "Title"` |
| **Warning block** | Required step; skipping it causes failure or bad UX | `!!! warning "Title"` |
| **Platform tabs** | Same topic, different steps per OS (Windows / macOS) | `=== "Windows"` / `=== "macOS"` |
| **Recipe hub** | Index page linking to focused workflow pages | `docs/users/recipes/index.md` |
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

Live example: [Install the desktop app](../users/install.md).

Reference: [Material content tabs](https://squidfunk.github.io/mkdocs-material/reference/content-tabs/).

---

## Other patterns in use

### Home cards

The home page uses Material grid cards for primary CTAs (web app, desktop install, audience guides).
See `docs/index.md`.

### External links

Add `{target="_blank" rel="noopener"}` to links that leave the doc site (GitHub Releases, web app, etc.).

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

## Adding new patterns

Before introducing a new Material feature (e.g. diagrams, annotations, new admonition types):

1. Confirm the extension is listed in `mkdocs.yml` `markdown_extensions` or `theme.features`.
2. Add one canonical example to this guide.
3. Add a row to the quick reference table at the top.
