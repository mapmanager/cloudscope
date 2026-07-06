# CloudScope Agent Instructions

## Mission

Build CloudScope as a thin frontend over strong backend and reusable widget packages.

CloudScope currently has three source packages in this repository:

- `src/acqstore/`: backend acquisition/data-model code
- `src/nicewidgets/`: reusable, general-purpose NiceGUI widgets
- `src/cloudscope/`: CloudScope app code, contracts, controller/event/state logic, and GUI

---

## Package Boundaries (STRICT)

- Backend acquisition models, file loaders, ROI models, metadata models, analysis models, schemas, and persistence helpers belong in `src/acqstore/`.
- Reusable NiceGUI widgets that should not know about CloudScope belong in `src/nicewidgets/`.
- CloudScope contracts, controller/event/state logic, app orchestration, adapters, and GUI composition belong in `src/cloudscope/`.
- NiceGUI-specific CloudScope app code belongs in `src/cloudscope/gui/`.

### Boundary Rules

- Do NOT move code across the `acqstore` / `nicewidgets` / `cloudscope` boundaries unless the ticket explicitly asks for it.
- `acqstore` MUST NOT import from `cloudscope` or `nicewidgets`.
- `nicewidgets` MUST NOT import from `cloudscope`.
- Do NOT modify GUI code unless the ticket explicitly asks for GUI work.
- Do NOT modify files outside the scope of the current ticket.
- Do NOT modify repo root **`README.md`** as part of other work (see **`README.md`
  (STRICT)** under Coding Rules).
- If a required change appears to require cross-cutting refactors, STOP and report instead of guessing.

---

## Core Principles

- Views emit intent only.
- Controller handles orchestration logic.
- Backend owns data and rules.
- No hidden defaults.
- Prefer fail-fast behavior over silent coercion.
- Backend APIs must use backend-native values and must not leak GUI assumptions.
- Keep package APIs explicit; do not add imports or behavior in `__init__.py`
  except for the **frozen curated public API allowlist** (see **`__init__.py`
  (STRICT)** under Coding Rules).

---

## Coding Rules

- All public APIs must be fully typed.
- All public APIs must have Google-style docstrings.
- Docstrings must include Args, Returns, and Raises when applicable.
- Keep implementations KISS and DRY.
- Avoid speculative abstraction.
- Avoid backward compatibility unless explicitly required by the ticket.
- Fail fast on invalid input with clear exceptions.
- Do not invent APIs, behaviors, file locations, or naming conventions that are not specified by the ticket or existing source of truth.

### `__init__.py` (STRICT)

**Default: empty.** New or updated `__init__.py` files MUST be empty (no
docstring, imports, `__all__`, comments, compatibility aliases, or import side
effects) unless the ticket **explicitly** adds or modifies a curated public API
surface.

When creating a new package directory, add an empty `__init__.py` only to mark
the directory as a package. Put module and package documentation on the primary
`.py` module, not on `__init__.py`.

**Import style:** use explicit module paths everywhere else, for example
`from acqstore.acq_image.acq_image import AcqImage`. Do not add barrel imports
“for convenience” or “discoverability”.

**Do not** “clean up”, empty, or rewrite allowlisted curated API files to match
the default-empty rule unless the ticket **explicitly names the file** and the
symbols to add or remove.

**Frozen curated public API allowlist** (do not modify without an explicit
ticket request that names the file and symbols):

| File | Re-exported symbols |
|---|---|
| `src/acqstore/acq_image/__init__.py` | `AcqImage`, `AcqImageList`, `AcqPixels` |
| `src/acqstore/acq_image/analysis/__init__.py` | `RadonVelocityAnalysis`, `DiameterAnalysis`, `HeartRateAnalysis`, `EventAnalysis` |
| `src/acqstore/acq_image/analysis/batch/__init__.py` | batch types and strategies (see file `__all__`) |
| `src/nicewidgets/nicepool/__init__.py` | NicePool public widget API (see file `__all__`) |
| `src/nicewidgets/upload_widget/__init__.py` | `CancelToken`, `UploadWidget` |

The acqstore curated import contract is tested in
`tests/acqstore/test_public_imports.py`. Keep those tests passing when changing
allowlisted files.

Top-level package roots stay empty unless a future ticket explicitly promotes
symbols (for example `src/acqstore/__init__.py` and `src/cloudscope/__init__.py`
are empty today).

See also `.cursor/rules/empty-init-py.mdc`.

### `README.md` (STRICT)

Repo root **`README.md`** is the public project overview on GitHub. It is **not**
maintained in real time as `src/`, `tests/`, or other code changes land.

**Do not** edit `README.md` when implementing feature, refactor, test, or docs
tickets unless the ticket **explicitly** asks for a README update.

Instead, during normal development:

- Put API and module detail in **Google-style docstrings** on the code.
- Put user-facing guides in **`docs/`** (MkDocs) when the ticket includes docs work.
- Put developer notes, architecture, and ticket reports in **`docs-dev/`**.
- Record follow-ups for a future README pass in the ticket report if needed.

**When to update `README.md`:** only in a **dedicated README ticket** after the
relevant API and `src/` changes are finalized — a deliberate rewrite pass, not
drive-by edits at the end of unrelated tickets.

This rule applies to repo root **`README.md`** only. It does not restrict
`README-DEV.md`, package-local readmes under `src/`, or **`docs/`** when those
files are in explicit ticket scope.

See also `.cursor/rules/no-readme-driveby.mdc`.

---

## Ticket Discipline (VERY IMPORTANT)

- Each ticket must be treated as a strict scope boundary.
- Implement only what the ticket asks.
- Do not anticipate future tickets.
- Do not add unrelated helpers, abstractions, or refactors.
- Do not modify contracts unless explicitly instructed.
- Do not update repo root **`README.md`** unless the ticket explicitly requests it.
- If something is unclear or underspecified, STOP and report instead of guessing.
- Do not consider a ticket complete unless its required report artifact exists.

---

## Required Ticket Report File

Every ticket worked in **Cursor** MUST create or update a report file under:

```text
docs-dev/cursor_tickets/
```

### Legacy `codex_tickets/` (frozen)

Older reports live in ``docs-dev/codex_tickets/``. **Do not** add, renumber, or
edit files there. New Cursor work uses ``cursor_tickets/`` only.

### Ticket numbering

Pick the next **unused three-digit prefix** by listing ``docs-dev/cursor_tickets/``
and finding the highest ``NNN_`` prefix (for example ``001_``). Use the next
integer for the new report:

```text
docs-dev/cursor_tickets/002_short_title_report.md
```

Older reports without a numeric prefix can be ignored for sequencing. The
descriptive slug after the number is free-form.

The report filename MUST include the ticket number and short title.

Example:

```text
docs-dev/cursor_tickets/001_disconnect_reconnect_handoff.md
```

### Handoff vs implementation tickets

- **Handoff / planning** tickets document problem, architecture, and an
  implementation spec for a follow-on ticket. They may omit “files changed”
  until work lands elsewhere.
- **Implementation** tickets MUST include the sections below when the ticket
  is complete.

Implementation report files MUST include:

- Files changed
- Summary of implementation
- Tests added or modified
- Exact test commands run
- Test results
- Any concerns or follow-ups

Do not treat a conversational summary as a substitute for the report file. The report must be a committed file in the repository unless the ticket explicitly says otherwise.

---

## Testing (STRICT)

All tests MUST be run using:

```bash
uv run pytest
```

For focused tests, use:

```bash
uv run pytest tests/<file>.py
```

Rules:

- Do NOT use plain `pytest`.
- Do NOT skip tests.
- New functionality MUST include tests.
- Edge cases MUST be tested.
- Tests must be deterministic.
- Test results must be recorded in the ticket report file.

### Test purpose and iteration

Unit tests verify intended API and module behavior; they are not written simply
to pass. Use this loop when tests fail:

1. Write a test that asserts intended behavior.
2. Run with `uv run pytest` (or a focused test file).
3. On failure, ask: **Is the API/source wrong, or is the test wrong?**
   - If the **API/source is wrong**: warn in chat, then fix the source.
   - If the **test is wrong**: fix the test while still asserting real behavior.
4. Repeat until tests pass for the right reasons.

Do not weaken assertions to match buggy code without flagging the API error. Do
not change production code to satisfy a bad test without confirming intended
behavior. See also `.cursor/rules/unit-test-discipline.mdc`.

---

## Structure

```text
src/
  acqstore/        # backend data/model layer
  nicewidgets/     # reusable NiceGUI widgets
  cloudscope/      # app, contracts, controller, GUI

tests/             # unit tests
docs/              # MkDocs site sources (published documentation)
docs-dev/          # architecture, tickets, review docs (developer docs)
scripts/           # development and API exercise scripts
```

---

## Packaged app entry point (PyInstaller / nicegui-pack)

When editing `src/cloudscope/app.py`, macOS packaging scripts, or desktop
launcher code that affects packaged startup:

- Follow `docs-dev/pyinstaller_nicegui_multiprocessing.md`.
- Use `multiprocessing.freeze_support()` under `if __name__ == "__main__":`.
- Do **not** launch the application from `__mp_main__`.
- Frozen builds must run with NiceGUI `reload=False`.

---

## Required Completion Output

After completing any ticket, provide a concise response that points to the report file and includes:

1. Files changed
2. Summary
3. Tests run
4. Test results
5. Concerns or follow-ups

The report file is still mandatory even if this response is provided.

---

## When Unsure

You are the senior developer on this project. Make high-level executive
decisions on your own.

Always follow the rule: **Ask, do not guess.**

If unsure of a source of truth for any statement or code you will write:

- Do NOT guess.
- Do NOT invent APIs, behaviors, file locations, or naming conventions.
- Do NOT silently change behavior or assume ticket scope beyond what is stated.
- Investigate the codebase and existing docs first.

If still ambiguous:

- Stop.
- Explain the ambiguity.
- Ask for clarification in chat.
- **Include a recommended solution** with every question — state what you
  would do and why.
