# 057 — AcqStore public import surface

## Summary

Added curated public re-export surfaces in `acqstore` so notebooks and scripts
can use shorter, stable import paths without changing internal module layout.

Public imports now supported:

```python
from acqstore.acq_image import AcqImage, AcqImageList
from acqstore.acq_image.analysis import (
    DiameterAnalysis,
    EventAnalysis,
    HeartRateAnalysis,
    RadonVelocityAnalysis,
)
```

Deep import paths remain valid and unchanged for existing `src/cloudscope`,
`src/acqstore` internals, and `tests/`.

Also updated `AGENTS.md` to allow explicitly curated `__all__`-documented
re-export surfaces for stable public APIs.

## Files changed

- `AGENTS.md`
- `src/acqstore/acq_image/__init__.py`
- `src/acqstore/acq_image/analysis/__init__.py`
- `tests/acqstore/test_public_imports.py`
- `scripts/acqstore/try_acq_analysis.py`
- `scripts/acqstore/try_acq_image.py`
- `scripts/acqstore/try_acq_image_list.py`
- `scripts/acqstore/try_create_roi.py`
- `scripts/acqstore/try_diameter_analysis.py`
- `scripts/acqstore/try_diameter_batch.py`
- `scripts/acqstore/try_event_analysis.py`
- `scripts/acqstore/try_heart_rate_analysis.py`
- `scripts/acqstore/try_radon_analysis.py`
- `scripts/acqstore/try_radon_batch_analysis.py`
- `scripts/acqstore/try_velocity_batch.py`
- `docs/notebooks/diameter-analysis.ipynb`
- `docs/notebooks/heart-rate-analysis.ipynb`
- `docs/notebooks/heart-rate-batch-analysis.ipynb`
- `docs/notebooks/load-and-plot-image.ipynb`
- `docs/notebooks/velocity-analysis.ipynb`

## Tests added or modified

Added `tests/acqstore/test_public_imports.py`:

- `test_public_acq_image_imports`
- `test_public_analysis_imports`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_public_imports.py -q
uv run python -c "from acqstore.acq_image import AcqImage, AcqImageList; from acqstore.acq_image.analysis import RadonVelocityAnalysis, DiameterAnalysis, HeartRateAnalysis, EventAnalysis; print('imports ok')"
```

## Test results

```
2 passed in 0.01s
imports ok
```

Linters: no errors on changed source/test files.

## Concerns or follow-ups

- Non-public helpers such as `_build_file_list`, `get_allowed_import_extensions`,
  `PathKind`, and `EventType` remain on their deep module paths by design.
- `src/cloudscope` and existing `tests/` were intentionally left on deep paths;
  they can be migrated later if desired.
