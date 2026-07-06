# Ticket 015 — Final coverage verification

## Files changed

- `docs/codex_tickets/015_final_coverage_verification_report.md`
  (this report only — no source or test changes)

## Summary

Verification run after the 14 prior coverage tickets (001–014). The full
test suite passes and the omit list configured in ticket 001 is respected.

## Exact test commands run

```bash
uv run pytest --cov=src --cov-report=term -q
uv run pytest --cov=cloudscope --cov=nicewidgets --cov-report=term -q
uv run pytest --cov=cloudscope --cov-report=term -q
uv run pytest --cov=nicewidgets --cov-report=term -q
```

## Test results

- **723 / 723 tests passing** (3 harmless RuntimeWarnings from the
  intentional all-NaN test in `test_raster_service.py`)
- Coverage breakdown:

| Scope                       | Statements | Missed | Cover |
|----------------------------|-----------:|-------:|------:|
| Total (`--cov=src`)        | 9334       | 2530   | **73%** |
| `cloudscope` only          | 4358       | 1457   | 67%   |
| `nicewidgets` only         | 1831       | 331    | 82%   |
| `cloudscope` + `nicewidgets` | 6189     | 1788   | 71%   |

**Baseline before this work was 60%** → end state is **73%**, a +13
percentage point improvement.

## Per-ticket impact (focus modules only)

| Ticket | Module                                       | Before | After |
|-------:|-----------------------------------------------|-------:|------:|
| 002    | `controllers/analysis_controller.py`         | 28%    | high  |
| 003    | `controllers/event_analysis_controller.py`   | 28%    | high  |
| 004    | `controllers/load_save_controller.py`        | 72%    | high  |
| 005    | `views/load_save_view.py` helpers            | 36%    | partial |
| 006    | `views/metadata_widget/schema_card_widget.py`| 16%    | partial |
| 007    | `views/metadata_widget/metadata_view.py`     | 36%    | partial |
| 008    | `views/{velocity,diameter,event}_analysis_view.py` | ~20-25% | partial |
| 009    | `views/primary_image_view.py`                | 41%    | partial |
| 010    | `views/acq_analysis_plot_view.py`            | 49%    | high  |
| 011    | `nicewidgets/echart_widget/widget.py`        | 30%    | partial |
| 012    | `nicewidgets/raster_viewer/backend/raster_service.py` | < 50% | **100%** |
| 013    | `nicewidgets/raster_viewer/frontend/plotly_coord_transform.py` | 55% | **100%** |
| 013    | `nicewidgets/raster_viewer/frontend/plotly_protocol.py` | 55% | **98%** |
| 013    | `nicewidgets/raster_viewer/frontend/plotly_viewer.py` | 41% | 63% |
| 014    | `nicewidgets/image_toolbar_widget/image_toolbar_widget.py` | 64% | **100%** |

## Files changed across all tickets

Only `pyproject.toml` and files under `tests/` were modified, in line with
the agreed scope. The `docs/codex_tickets/` directory received one report
file per ticket (001 through 015).

### `pyproject.toml`

Added a `[tool.coverage.run] omit` section (ticket 001) excluding:

- `src/cloudscope/app.py`
- `src/cloudscope/devtools/*`
- `src/nicewidgets/raster_viewer/demo/*`
- `src/nicewidgets/table_widget/demo_app.py`
- `src/nicewidgets/gui_defaults.py`

### Test files added

- `tests/cloudscope/test_analysis_controller.py` (expanded)
- `tests/cloudscope/test_event_analysis_controller.py` (new)
- `tests/cloudscope/test_load_save_controller.py` (expanded)
- `tests/cloudscope/test_load_save_view.py` (new)
- `tests/cloudscope/test_schema_card_widget.py` (new)
- `tests/cloudscope/test_metadata_view.py` (new)
- `tests/cloudscope/test_velocity_analysis_view.py` (new)
- `tests/cloudscope/test_diameter_analysis_view.py` (new)
- `tests/cloudscope/test_event_analysis_view.py` (new)
- `tests/cloudscope/test_primary_image_view_handlers.py` (new)
- `tests/cloudscope/test_acq_analysis_plot_view.py` (expanded)
- `tests/nicewidgets/test_echart_widget.py` (expanded)
- `tests/nicewidgets/test_raster_service.py` (new)
- `tests/nicewidgets/test_plotly_viewer_state.py` (new)
- `tests/nicewidgets/test_image_toolbar_widget_handlers.py` (new)

## Concerns or follow-ups

- `plotly_viewer.py` (63%) still has uncovered methods that push JavaScript
  through `self._plot.client.run_javascript(...)`. Lifting that further
  would require a substantial fake of NiceGUI `Element`/`client` or
  Playwright-style integration tests — out of scope for the test-only
  coverage tickets.
- The remaining low-coverage hotspots outside the agreed scope include
  `cloudscope/views/home_page_view.py`, the larger GUI shells, and a few
  `nicewidgets/utils/` modules (`clipboard.py`, `logging.py`). These were
  intentionally not addressed under the "tests/ + pyproject.toml only"
  scope and could each be a follow-up ticket.
- The two intentional RuntimeWarnings in `test_raster_service.py` are
  expected (all-NaN PNG path) and could be suppressed with a future
  `np.errstate(...)` block inside the service, but that would be a source
  change and is out of scope here.
