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

### Rules

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

- Each ticket must be treated as a **strict scope boundary**.
- Implement only what the ticket asks.
- Do not “anticipate” future tickets.
- Do not add unrelated helpers, abstractions, or refactors.
- Do not modify contracts unless explicitly instructed.
- If something is unclear or underspecified, STOP and report.

---

## Testing (STRICT)

All tests MUST be run using:

```bash
uv run pytest