# AcqStore Schemas

This document defines backend-owned semantic schemas that GUI layers consume.

## Design Goals

- Backend defines schema and values once.
- One schema supports both table and card views.
- GUI toolkits map schema hints to concrete widgets and columns.
- Schema serialization is forward-compatible (unknown keys ignored).

## Schema Envelope

Each schema is represented by:

- `schema_id`: stable key, for example `acq_file_list`
- `version`: integer schema version
- `fields`: ordered list of semantic field definitions

Ordering is the list order in `fields`.

## Field Definition

Each field includes:

- identity: `name`, `display_name`
- semantics: `value_type`, `semantic_kind`, `description`, `unit`
- constraints: `required`, `default`, `choices`
- table hints: visibility/editability/sort/filter/width/pin/format
- card hints: visibility/editability/control/group/multiline

## Semantic Kinds (v1)

`semantic_kind` values currently include:

- `id`
- `name`
- `path`
- `count`
- `status`
- `metric`
- `other`

These are GUI-agnostic hints for consistent rendering behavior.

## v1: `acq_file_list`

Schema id: `acq_file_list`  
Version: `1`

Fields:

1. `path` (`value_type=path`, `semantic_kind=path`)
2. `num_channels` (`value_type=int`, `semantic_kind=count`)
3. `num_rois` (`value_type=int`, `semantic_kind=count`)

## Planned AcqImage JSON Persistence

AcqImage JSON persistence is intended to include:

- multiple schema definitions keyed by schema id
- schema-driven values for metadata sections
- non-schema payloads such as ROI data

This keeps metadata contracts explicit while letting ROI serialization evolve independently.
