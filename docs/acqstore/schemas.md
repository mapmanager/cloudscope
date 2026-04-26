# AcqStore Schemas

This document defines backend-owned semantic schemas that GUI layers consume.

## Design Goals

- Keep `acqstore` independent from any GUI package.
- Keep schema definitions concise and readable.
- Expose one semantic schema usable for table and card UIs.
- Fail fast when schema rows drift from schema field definitions.

## Supported import file formats

Canonical extensions (no leading dot, case-insensitive on disk) live in
`acqstore.acq_image.supported_import_extensions` as `ALLOWED_IMPORT_EXTENSIONS`.
Only `.tif`, `.oir`, and `.czi` are supported; `.tiff` is intentionally unsupported.

## Schema Envelope

Each schema is represented by:

- `schema_id`: stable key, for example `acq_file_list`
- `version`: integer schema version
- `fields`: ordered list of semantic field definitions

Field order in `fields` is the canonical display order.

## Field Definition

Each field includes:

- identity: `name`, `display_name`
- semantics: `value_type`, `description`, `unit`
- constraints: `required`, `default`, `choices`
- display/edit hints: `visible`, `editable`, `group`

No GUI widget types are encoded in `acqstore`. GUI code infers widgets from these semantic attributes.

## Validation

`acqstore.schema` provides:

- `validate_schema_field_names()`
- `validate_values_for_schema()` (strict by default)
- `validate_patch_for_schema()` for validating GUI edit patches

Default row validation is strict:

- `require_visible_fields=True`
- `allow_extra_values=False`

## v1: `acq_file_list`

Schema id: `acq_file_list`  
Version: `1`

Fields:

1. `name` (`value_type=str`)
2. `path` (`value_type=path`)
3. `num_channels` (`value_type=int`)
4. `num_rois` (`value_type=int`)
