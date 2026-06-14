"""Try the acqstore native OME-Zarr round trip from the command line.

This is intentionally a small development script, not a polished CLI. It helps
exercise the first AcqPixels / OME-Zarr implementation against real local files:

1. Load one source acquisition file or store, such as ``.oir``, ``.czi``,
   ``.tif``, ``.ome.zarr``, or ``.cs.ome.zarr``.
2. Hydrate any existing acqstore sidecars next to the source file using the
   normal :class:`AcqImage` constructor.
3. Save a native single-acquisition ``.cs.ome.zarr`` store with embedded
   acqstore metadata and analysis sidecars.
4. Reload that store through the normal loader path and print a summary.

Example:
    uv run python scripts/try_ome_zarr.py /path/to/source.oir --output /tmp/source.cs.ome.zarr --overwrite
"""

from __future__ import annotations

import argparse
from pathlib import Path

from acqstore.acq_image import AcqImage
from acqstore.acq_image import AcqImageList


def _default_output_path(source: Path) -> Path:
    name = source.name
    for suffix in (".cs.ome.zarr", ".ome.zarr"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    else:
        name = source.stem
    return source.with_name(f"{name}.cs.ome.zarr")


def _print_summary(label: str, acq: AcqImage) -> None:
    pixels = acq.pixels
    print(f"\n{label}")
    print("-" * len(label))
    print(f"path: {acq.path}")
    print(f"name: {acq.name}")
    print(f"axes: {pixels.axes}")
    print(f"shape: {pixels.shape}")
    print(f"dtype: {pixels.dtype}")
    print(f"channels: {pixels.num_channels}")
    print(f"physical_units: {pixels.header.physical_units}")
    print(f"physical_units_labels: {pixels.header.physical_units_labels}")
    print(f"roi_count: {acq.rois.num_rois}")
    print(f"analysis_count: {len(acq.analysis_set.as_list())}")
    for section in acq.get_metadata_sections():
        print(f"metadata[{section.metadata_section_id}]: {section.get_values()}")


def main() -> None:
    path = '/Users/cudmore/Sites/cloudscope-data/demo-velocity/20251030'
    acqimagelist = AcqImageList(path)
    
    acqimage = acqimagelist.get_file_by_index(0)

    # loaded = AcqImage(path)
    _print_summary("Loaded acqimage", acqimage)

    output = '/Users/cudmore/Desktop/tst.cs.ome.zarr'
    overwrite = True

    acqimage.save_native_zarr(output, overwrite=overwrite)
    print(f"\nSaved native store: {output}")

    reloaded = AcqImage(str(output))
    _print_summary("Reloaded native store", reloaded)


if __name__ == "__main__":
    main()
