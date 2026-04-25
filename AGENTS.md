# CloudScope Agent Instructions

## Mission

Build CloudScope as a thin frontend over a strong backend.

CloudScope is split into two packages in this repository:

- `src/acqstore/`: backend acquisition/data-model code
- `src/cloudscope/`: CloudScope app code, contracts, controller/event/state logic, and GUI

---

## Package Boundaries (STRICT)

- Backend acquisition models, file loaders, ROI models, metadata models, and analysis models belong in `src/acqstore/`.
- CloudScope contracts, controller/event/state logic, app orchestration, and NiceGUI code belong in `src/cloudscope/`.
- NiceGUI-specific code belongs only in `src/cloudscope/gui/`.

### Boundary Rules

- Do NOT move code across the `acqstore` / `cloudscope` boundary unless the ticket explicitly asks for it.
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

---

## Coding Rules

- All public APIs must be fully typed.
- All public APIs must have Google-style docstrings.
- Keep implementations KISS and DRY.
- Avoid speculative abstraction.
- Avoid backward compatibility unless explicitly required.
- Fail fast on invalid input with clear exceptions.
- Do not invent APIs, behaviors, or file locations that are not specified by the ticket or existing source of truth.

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
docs/tickets/reports/
```

The report filename MUST include the ticket number and short title.

Example:

```text
docs/tickets/reports/001_add_import_path_discovery_report.md
```

The report file MUST include:

- Files changed
- Summary of implementation
- Tests added or modified
- Exact test commands run
- Test results
- Any concerns or follow-ups

Do not treat a conversational summary as a substitute for the report file. The report must be a committed file in the repository.

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
  cloudscope/      # app, contracts, controller, GUI

tests/             # unit tests
docs/              # architecture, tickets, review docs
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

- Follow `docs/code_review.md` for quality standards.
- Use it as validation before completing a task.

---

## When Unsure

- Do NOT guess.
- Do NOT invent APIs.
- Do NOT silently change behavior.

Instead:

- Stop.
- Explain the ambiguity.
- Ask for clarification.
