# CloudScope Project Rules

## Repository Layout

The main project root is `cloudscope/`.

```text
cloudscope/
  pyproject.toml
  src/
  tests/
  docs/
```

`cloudscope/pyproject.toml` is the source-of-truth project configuration.

## Source Layout

All source packages live under:

```text
cloudscope/src/
```

Current packages:

```text
src/acqstore/
src/cloudscope/
src/nicewidgets/
```

## Test Layout

All tests live under the top-level project directory:

```text
cloudscope/tests/
```

Never place tests under `src/`.

Use exactly one package-level grouping directory under `tests/`:

```text
tests/acqstore/
tests/cloudscope/
tests/nicewidgets/
```

Do not mirror the full `src/` package tree under `tests/`. Keep test files directly in the package-level grouping directory.

Correct examples:

```text
tests/acqstore/test_event_analysis.py
tests/acqstore/test_acq_analysis_set.py
tests/cloudscope/test_event_analysis_controller.py
tests/nicewidgets/test_table_widget.py
```

Incorrect examples:

```text
src/cloudscope/tests/
src/acqstore/tests/
tests/acqstore/acq_image/analysis/event_analysis/test_event_analysis.py
tests/cloudscope/controllers/test_event_analysis_controller.py
```

## Package Boundary Rules

### acqstore

`acqstore` is the backend engine and data model layer.

Rules:

- Must not import `cloudscope`
- Must not import `nicewidgets`
- Owns analysis semantics
- Owns JSON serialization semantics
- Owns schema definitions
- Owns canonical analysis APIs

### nicewidgets

`nicewidgets` contains reusable GUI widgets.

Rules:

- Must not import `cloudscope`
- May depend on NiceGUI
- Should remain reusable outside the CloudScope app

### cloudscope

`cloudscope` is the application orchestration layer.

Rules:

- May import `acqstore`
- May import `nicewidgets`
- Owns controllers, views, event routing, and app composition

## API Rules

- Prefer explicit APIs over compatibility wrappers
- Do not add backward compatibility unless explicitly requested
- Current source code defines JSON serialization truth
- Prefer fail-fast validation over silent coercion
- Keep `__init__.py` files minimal or empty
- Avoid package-level re-export APIs unless explicitly needed

## Analysis Rules

Dependent analyses should consume canonical plot APIs rather than raw table columns.

Example:

```python
analysis.get_plot_data()
```

rather than directly reading analysis-specific dataframe columns.

## Documentation Rules

- Use Google-style docstrings
- Keep architecture docs updated with major refactors
- Keep package boundaries documented explicitly
- Add tests for all new backend analysis behavior

## Development Workflow

- Produce targeted replacement zips containing only edited/new files
- Preserve full relative paths from project root
- Run focused pytest subsets whenever possible
- Report exactly which tests were executed
