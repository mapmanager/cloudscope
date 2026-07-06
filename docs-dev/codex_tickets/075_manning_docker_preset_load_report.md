# Manning docker preset folder load

## Files changed

- `docker-compose.yml`
- `src/cloudscope/preset_data.py` (new)
- `src/cloudscope/views/load_save_view.py`
- `tests/cloudscope/test_preset_data.py` (new)
- `tests/cloudscope/test_load_save_view.py`
- `docs-dev/codex_tickets/075_manning_docker_preset_load_report.md`

## Summary of implementation

- Added read-only bind mount
  `../cloudscope-data/data/manning_velocity_20260625` →
  `/data/presets/manning_velocity_20260625` on both `cloudscope` and
  `cloudscope-dev`.
- Set `CLOUDSCOPE_PRESET_DATA_MANNING` in compose for the in-container path.
- Added `preset_data.py` to resolve the env var and detect loadable preset
  folders (directory with at least one importable acquisition file).
- Added **Load Manning Velocity 2026** to the history/hamburger menu for
  server/docker contexts only. Publishes existing `LoadPathIntent` (folder
  load). Menu item is disabled when the preset path is missing or empty.
- No controller, intent, or `acqstore` changes.

## Tests added or modified

- Added: `tests/cloudscope/test_preset_data.py`
- Modified: `tests/cloudscope/test_load_save_view.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_preset_data.py tests/cloudscope/test_load_save_view.py -q
```

## Test results

```
uv run pytest tests/cloudscope/test_preset_data.py tests/cloudscope/test_load_save_view.py -q
.........................................                                [100%]
41 passed in 1.67s
```

## Concerns or follow-ups

- Docker creates an empty host directory when the bind source is missing;
  create `cloudscope-data/data/manning_velocity_20260625` before `docker compose up`.
- Oracle layout assumes `cloudscope` and `cloudscope-data` are sibling
  directories under the deploy user home.
