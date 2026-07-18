# AcqStore Server v2 implementation slice 001

This slice:

- moves the existing v1 API/open-service tests into `tests/acqstore_server/v1/` without changing their test logic;
- adds `test_v1_linescan_client_contract`;
- creates the independent `acqstore_server.v2` package;
- adds strict Pydantic v2 request/response schemas;
- adds generic channel-indexed v2 session storage;
- adds focused v2 schema and session-store tests;
- starts `docs-dev/acqstore_server/v2/README.md`.

No v1 production module is edited.

Validation performed in the isolated extraction:

- Python `compileall`: passed.
- Full pytest: not completed because dependency synchronization for the extracted repository timed out before pytest was installed.

Recommended local validation:

```bash
uv sync --frozen --dev
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server/v2 tests/acqstore_server/v1 tests/acqstore_server/v2
```
