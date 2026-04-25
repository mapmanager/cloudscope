# CloudScope Agent Instructions

## Mission

Build CloudScope as a thin frontend over a strong backend.

CloudScope is split into two packages in this repository:

- src/acqstore/: backend acquisition/data-model code
- src/cloudscope/: CloudScope app code, contracts, controller/event/state logic, and GUI

---

## Package Boundaries (STRICT)

- Backend acquisition models, file loaders, ROI models, metadata models, and analysis models belong in src/acqstore/.
- CloudScope contracts, controller/event/state logic, app orchestration, and NiceGUI code belong in src/cloudscope/.
- NiceGUI-specific code belongs only in src/cloudscope/gui/.

### Rules

- Do NOT move code across the acqstore / cloudscope boundary unless the ticket explicitly asks for it.
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
- Backend APIs must use backend-native values (no GUI leakage).

---

## Coding Rules

- All public APIs must be fully typed.
- All public APIs must have Google-style docstrings.
- Keep implementations KISS and DRY.
- Avoid speculative abstraction.
- Avoid backward compatibility unless explicitly required.
- Fail fast on invalid input (raise clear exceptions).

---

## Ticket Discipline (VERY IMPORTANT)

- Each ticket must be treated as a strict scope boundary.
- Implement only what the ticket asks.
- Do not anticipate future tickets.
- Do not add unrelated helpers, abstractions, or refactors.
- Do not modify contracts unless explicitly instructed.
- If something is unclear or underspecified, STOP and report.

---

## Testing (STRICT)

All tests MUST be run using:

uv run pytest

For focused tests:

uv run pytest tests/<file>.py

Rules:

- Do NOT use plain pytest
- Do NOT skip tests
- New functionality MUST include tests
- Edge cases MUST be tested
- Tests must be deterministic (no flaky behavior)

---

## Structure

src/
  acqstore/        # backend data/model layer
  cloudscope/      # app, contracts, controller, GUI

tests/             # unit tests
docs/              # architecture, tickets, review docs

---

## Required Completion Output (MANDATORY)

After completing any ticket, you MUST provide:

1. Files Changed
- List all modified/created files with full paths

2. Summary
- Concise, technical description of what was implemented

3. Tests
- Tests added or modified

4. Test Execution
- Exact command used (must be uv run pytest)
- Test results (pass/fail)

5. Concerns / Follow-ups
- Any uncertainties
- Any assumptions made
- Any recommended next steps

Failure to include this section is considered incomplete work.

---

## Interaction with Code Review

- Follow docs/code_review.md for quality standards
- Do NOT duplicate its checklist here
- Use it as validation before completing a task

---

## When Unsure

- Do NOT guess
- Do NOT invent APIs
- Do NOT silently change behavior

Instead:

- Stop
- Explain the ambiguity
- Ask for clarification
