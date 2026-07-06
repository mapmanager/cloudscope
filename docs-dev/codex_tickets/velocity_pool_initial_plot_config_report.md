# Velocity pool initial_plot_config

## Files changed

- `src/nicewidgets/nicepool/plot_pool_controller.py`
- `src/nicewidgets/nicepool/config.py`
- `src/nicewidgets/nicepool/nice_pool.py`
- `src/cloudscope/views/velocity_pool_plot_config.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `tests/nicewidgets/test_plot_pool_controller.py`
- `tests/cloudscope/test_velocity_pool_view.py`

## Summary of implementation

- Added `initial_plot_config` to `PlotPoolConfig` / `NicePoolConfig`: inline dict
  with `layout`, `plot_states`, and optional `control_panel_splitter_value`.
- Applied at controller init via existing `sanitize_preset_payload()` validation.
- Takes precedence over session persistence (`enable_config_persistence`) when set.
- Added CloudScope-owned `VELOCITY_POOL_INITIAL_PLOT_CONFIG` and wired Velocity
  Pool view to pass it with persistence still disabled.

## Tests added or modified

- Added: `test_initial_plot_config_applies_layout_and_plot_states`
- Added: `test_initial_plot_config_overrides_session_persistence`
- Modified: `test_velocity_pool_view_configures_initial_plot_config`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plot_pool_controller.py tests/cloudscope/test_velocity_pool_view.py -q
```

## Test results

- **21 passed**

## Concerns or follow-ups

- Edit `VELOCITY_POOL_INITIAL_PLOT_CONFIG` in CloudScope to change velocity-pool
  first-run plots without touching nicewidgets or user preset files.
