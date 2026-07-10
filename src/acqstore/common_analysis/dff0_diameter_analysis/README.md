# DFF0–Diameter Analysis

Pure-Python cross-analysis between a continuous functional reporter trace and a simultaneously measured diameter trace. Reporter peak onsets are upstream seeds; this package does not redetect those seeds.

The core algorithm is domain-independent:

```python
analyze_triggered_events(time, signal, seed_indices, params)
```

The diameter use case measures what the diameter was doing before each reporter seed and what response occurred after it, bounded by the next seed or the signal end.

## Run tests

```bash
uv run pytest src/acqstore/common_analysis/dff0_diameter_analysis/tests
```

## Run the exploratory app

```bash
uv run python -m acqstore.common_analysis.dff0_diameter_analysis.app.main
```

See `docs/current-state.md` and `docs/decisions.md` for the durable project handoff.
