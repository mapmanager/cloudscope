# Ticket 010 — Representative format integration tests

## Goal

Add optional, behavioral API v2 integration coverage for the regular-file acquisition formats most relevant to current clients: TIFF, OIR, CZI, and ND2.

## Scope

Edited files are limited to:

- `tests/acqstore_server/`
- `docs-dev/acqstore_server/`

No production server code was changed.

## Read-only AcqStore inspection

Before implementing the tests, the relevant public loader path was checked in read-only `src/acqstore/`, including:

- `acqstore.acq_image.acq_image.AcqImage`
- TIFF, OIR, CZI, and ND2 loader registration/implementations
- the existing `AcqImage.pixels`, channel-plane, physical-unit, and reference-image behavior already consumed by API v2

Nothing under `src/acqstore/` was edited.

## Implementation

Added:

- `tests/acqstore_server/v2/representative_files.py`
- `tests/acqstore_server/v2/test_representative_formats.py`
- `docs-dev/acqstore_server/v2/representative-format-testing.md`

Updated:

- `docs-dev/acqstore_server/v2/README.md`

## Fixture configuration

Tests accept either format-specific environment variables:

- `ACQSTORE_SERVER_TEST_TIF`
- `ACQSTORE_SERVER_TEST_OIR`
- `ACQSTORE_SERVER_TEST_CZI`
- `ACQSTORE_SERVER_TEST_ND2`

or a shared recursive search root:

- `ACQSTORE_SERVER_TEST_DATA_DIR`

Missing samples skip cleanly. Explicitly configured missing paths fail visibly.

## API-first failure policy

Once a representative path is configured, a non-200 `/api/v2/open` result is reported as an API error with its complete response body. The test does not rewrite expectations or skip a configured loader failure.

## Contract verified

Each configured format is opened through HTTP and checked for:

- generic source-channel selection;
- source name, path, format, dtype, and channel count;
- two-dimensional plane shape and calibrated `Y, X` axes;
- raw little-endian float32 byte count and decoding;
- session metadata;
- explicit deletion and expired binary URLs.

## Zarr boundary

No new Zarr-specific behavior or test fixtures were added. Existing support remains untouched; active format coverage is focused on TIFF, OIR, CZI, and ND2.
