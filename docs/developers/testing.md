# Testing

Run the test suite with:

```bash
uv run pytest
```

Run tests with coverage:

```bash
uv run pytest \
  --cov=src/cloudscope \
  --cov=src/acqstore \
  --cov=src/nicewidgets \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml
```
