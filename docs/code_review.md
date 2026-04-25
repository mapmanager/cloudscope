# Code Review Guidelines

## Goals

Ensure CloudScope maintains:

- thin frontend
- strong backend APIs
- explicit state and event flow
- clear package boundaries
- high test coverage for logic

## Review Checklist

### 1. Package Boundaries

- Does backend/data-model logic live in `src/acqstore/`?
- Does NiceGUI code live only in `src/cloudscope/gui/`?
- Did the change avoid moving code across package boundaries unless explicitly requested?

### 2. Backend vs GUI

- Was logic added to GUI that belongs in backend?
- Could repeated GUI code be moved into `acqstore`, `cloudscope.core`, or a shared widget API?

### 3. Public API

- Are public function and method parameters typed?
- Are return types typed?
- Are Google-style docstrings present?
- Do docstrings explain parameter purpose?
- Are names explicit and backend-native?

### 4. Explicit Behavior

- Are there hidden defaults?
- Is there silent coercion?
- Does invalid input fail clearly?

### 5. Tests

- Are new behaviors tested?
- Are edge cases covered?
- Were tests run with `uv run pytest` or a focused `uv run pytest tests/...` command?

### 6. Simplicity

- Is the code KISS?
- Is duplication avoided?
- Is the change scoped to the ticket?

## Output Format for Codex

Report:

- Files changed
- Summary
- Tests run
- Any concerns
