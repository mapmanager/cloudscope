# Ticket 003 — Fix v2 AcqImage loader access

## Problem

The first v2 open-service implementation attempted to access:

```python
acq.images.file_loader
```

This was incorrect. `AcqImage.images` already returns the active
`BaseFileLoader`; concrete loaders such as `TiffFileLoader` do not expose a
nested `file_loader` attribute.

The error caused all successful v2 open-service paths to fail with:

```text
AttributeError: 'TiffFileLoader' object has no attribute 'file_loader'
```

## Correction

Use the established AcqStore access pattern already used by the frozen v1
service:

```python
loader = acq.images
if loader.has_reference_image:
    reference = loader.reference_image
```

No v1 production code was edited.

## Files edited

```text
src/acqstore_server/v2/open_service.py
```

## Validation

- Confirmed from `AcqImage.images` that it returns `BaseFileLoader` directly.
- Confirmed `BaseFileLoader` defines `has_reference_image` and
  `reference_image` properties.
- Python syntax compilation passed.

## Regression coverage

The existing v2 tests exercise this path for ordinary TIFF files and mocked
reference images:

```text
tests/acqstore_server/v2/test_open_service.py
tests/acqstore_server/v2/test_reference.py
```
