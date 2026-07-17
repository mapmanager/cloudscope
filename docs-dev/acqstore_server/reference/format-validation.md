# Format validation

## Loader capability versus integration validation

`GET /api/v2/capabilities` reports formats registered and allowed by the current AcqStore runtime. This confirms loader availability; it does not prove that every vendor-file variant has been exercised through the HTTP API.

The v2 open service now accepts both files and directory-backed acquisitions and uses AcqStore's compound-extension normalization. This is required for paths such as:

```text
sample.ome.zarr
sample.cs.ome.zarr
sample.ome.zarr.zip
sample.cs.ome.zarr.zip
```

## Current automated coverage

- single-channel TIFF;
- multi-channel TIFF;
- arbitrary ordered channel selection;
- reference-image channels and coordinates;
- compound OME-Zarr extension normalization;
- directory-backed acquisition paths reaching the AcqStore loader boundary.

## Representative-file validation still required

Add integration fixtures or opt-in local tests for representative:

- OIR;
- CZI;
- ND2;
- OME-Zarr directory and ZIP stores.

These tests must use actual representative acquisitions. Do not simulate vendor metadata and claim format validation.
