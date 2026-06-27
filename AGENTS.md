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
- If a required change appears to require cross-cutting refactors, STOP and report instead of guessing.

---

## Core Principles

- Views emit intent only.
- Controller handles orchestration logic.
- Backend owns data and rules.
- No hidden defaults.
- Prefer fail-fast behavior over silent coercion.
- Backend APIs must use backend-native values and must not leak GUI assumptions.
- Keep package APIs explicit; avoid hiding imports or behavior in `__init__.py`
  except for intentionally curated public re-export surfaces documented with
  `__all__`.

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
- Keep `__init__.py` files minimal. Do not add re-export lists or import side
  effects unless the ticket explicitly asks for them. Curated public re-export
  surfaces are allowed when they are explicit, documented with `__all__`, and
  limited to stable public APIs.

---

## Ticket Discipline (VERY IMPORTANT)

- Each ticket must be treated as a strict scope boundary.
- Implement only what the ticket asks.
- Do not anticipate future tickets.
- Do not add unrelated helpers, abstractions, or refactors.
- Do not modify contracts unless explicitly instructed.
- If something is unclear or underspecified, STOP and report instead of guessing.
- Do not consider a ticket complete unless its required report artifact exists.

---

## Required Ticket Report File

Every ticket MUST create or update a report file under:

```text
docs-dev/codex_tickets/
```

The report filename MUST include the ticket number and short title.

Example:

```text
docs-dev/codex_tickets/001_add_import_path_discovery_report.md
```

The report file MUST include:

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
