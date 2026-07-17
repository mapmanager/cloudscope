# Representative format testing

API v2 has optional behavioral integration tests for the primary regular-file formats used by current clients:

- TIFF
- OIR
- CZI
- ND2

The tests use real local files but do not commit microscopy datasets to the repository. They skip cleanly when no local sample is configured.

## Configure individual files

Set one or more absolute paths:

```bash
export ACQSTORE_SERVER_TEST_TIF=/path/to/sample.tif
export ACQSTORE_SERVER_TEST_OIR=/path/to/sample.oir
export ACQSTORE_SERVER_TEST_CZI=/path/to/sample.czi
export ACQSTORE_SERVER_TEST_ND2=/path/to/sample.nd2
```

Then run:

```bash
uv run pytest tests/acqstore_server/v2/test_representative_formats.py -v
```

## Configure a sample directory

Alternatively, provide one directory:

```bash
export ACQSTORE_SERVER_TEST_DATA_DIR=/path/to/acquisition-samples
uv run pytest tests/acqstore_server/v2/test_representative_formats.py -v
```

For each format without an explicit path, the test resolver recursively chooses the first file with the matching extension. Format-specific variables take precedence over the directory.

## Failure behavior

An unavailable format is skipped. An explicitly configured missing path is a test configuration failure.

Once a file is configured, a non-successful `/api/v2/open` response is treated as an API failure and the test reports the HTTP status and complete error body. The test does not hide loader or server failures by skipping them.

## Behavioral contract

For each configured format, the test verifies that a generic client can:

1. open source channel `0`;
2. read source and plane metadata;
3. verify two-dimensional `Y, X` geometry and physical calibration;
4. download raw little-endian float32 data;
5. validate byte length and reshape using `plane.shape`;
6. inspect the live session;
7. delete the session and confirm its binary URL expires.

These tests deliberately avoid analysis-specific channel roles and client display orientation.

## Zarr scope

Existing generic Zarr path support remains in the server, but active representative-format development is focused on TIFF, OIR, CZI, and ND2. This test mechanism does not add Zarr-specific fixtures or behavior.
