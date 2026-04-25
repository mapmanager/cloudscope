# CloudScope Architecture

## Purpose

CloudScope is a NiceGUI-based application for loading, viewing, annotating, and analyzing acquisition-backed files through a thin frontend and strong backend API.

## Principles

- Thin GUI, strong backend
- Explicit APIs: fail fast, no hidden defaults
- Event-driven controller
- Stable identity: `file_id`, `roi_id`, backend-native `channel: int`
- Backend-native values in state/events
- No GUI logic leakage into backend models

## Repository Structure

```text
src/
  acqstore/
    acq_image/
      acq_image.py
      acq_image_list.py
      roi.py
      metadata.py
      acq_analysis.py
      file_loaders/

  cloudscope/
    core/
      contracts/
      controller.py
      event_bus.py
      events.py
      state.py
      utils/
    gui/

tests/
docs/
```

## Package Responsibilities

### `acqstore`

`acqstore` owns backend acquisition/data-model behavior.

It contains:

- acquisition image/file models
- acquisition image/file list models
- file discovery and file loading
- ROI models and ROI sets
- metadata models
- analysis models
- save/load behavior

`acqstore` must not depend on NiceGUI.

### `cloudscope`

`cloudscope` owns app-level orchestration and GUI.

It contains:

- contracts/protocols expected by the app
- controller and event bus
- state/event definitions
- NiceGUI views and pages

CloudScope GUI code should remain thin and should ask backend objects for data rather than duplicating backend logic.

## Domain Model

Primary backend model concepts:

- `AcqImage`
- `AcqImageList`
- helpers: images, rois, metadata, analysis

CloudScope contracts may use app-facing names such as:

- `AcqFileProtocol`
- `AcqFileListProtocol`
- `AcqRoisProtocol`

The concrete backend implementation may use different class names if the public API structurally satisfies the protocol.

## Event Model

Views emit intent events. Controllers subscribe to intent events, mutate state and backend objects, and publish state events. Views subscribe to state events.

Intent events include:

- `SelectFileIntent`
- `SelectChannelIntent`
- `SelectRoiIntent`
- `UpdateMetadataIntent`
- `RunAnalysisIntent`

State events include:

- `PrimarySelectionChanged`
- `RoiSelectionChanged`
- `FileListChanged`
- `MetadataChanged`
- `AnalysisFinished`

## Selection

Primary selection is:

```text
(file_id, channel, roi_id)
```

Selection values should be backend-native:

- `file_id`: stable file identifier
- `channel`: backend channel integer
- `roi_id`: backend ROI identifier

## Backend Contracts

Acquisition file objects expose helpers such as:

- `images`
- `rois`
- `metadata`
- `analysis`

Contracts live under:

```text
src/cloudscope/core/contracts/
```

Concrete backend implementation lives under:

```text
src/acqstore/
```

## Testing

Focus tests on:

- backend behavior
- controller/event logic
- state transitions
- serialization round trips
- file discovery
- fail-fast validation

GUI tests should focus on public view APIs and event wiring, not brittle low-level widget internals unless necessary.
