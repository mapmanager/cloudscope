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
- Keep package APIs explicit; avoid hiding imports or behavior in `__init__.py`.

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
- Keep `__init__.py` files minimal. Do not add re-export lists or import side effects unless the ticket explicitly asks for them.

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
docs/codex_tickets/
```

The report filename MUST include the ticket number and short title.

Example:

```text
docs/codex_tickets/001_add_import_path_discovery_report.md
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

---

## Structure

```text
src/
  acqstore/        # backend data/model layer
  nicewidgets/     # reusable NiceGUI widgets
  cloudscope/      # app, contracts, controller, GUI

tests/             # unit tests
docs/              # architecture, tickets, review docs
scripts/           # development and API exercise scripts
```

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

## Interaction with Code Review

- Follow `docs/code_review.md` for quality standards when present.
- Use it as validation before completing a task.
- If `docs/code_review.md` is absent or conflicts with the ticket, follow the current ticket.

---

## When Unsure

- Do NOT guess.
- Do NOT invent APIs.
- Do NOT silently change behavior.

Instead:

- Stop.
- Explain the ambiguity.
- Ask for clarification.
