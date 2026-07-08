# Supported file formats

CloudScope loads commercial microscopy formats and open image formats. The same
loaders are available in the desktop app and the browser app.

## Supported formats

CloudScope supports these **commercial microscopy formats**:

| Format | Extension | Notes |
|---|---|---|
| Olympus / Evident | `.oir` | Line-scan kymographs and reference/overview images. |
| Zeiss | `.czi` | Line-scan kymographs, reference images, and multi-line scan paths. |
| Nikon | `.nd2` | Nikon NIS-Elements acquisitions. |

and these **open image formats**:

| Format | Extension | Notes |
|---|---|---|
| TIFF | `.tif` | Generic TIFF image files, including multi-channel kymographs. |
| OME-Zarr | `.ome.zarr` | Directory-backed OME-Zarr stores. |

## Notes

- **Reference images.** OIR and CZI files often, but not always, include a
  reference or overview image and scan-path metadata. See
  [Kymograph reference images](../notebooks/kymograph-reference-image.ipynb).
- **Lazy loading.** Image pixels and analysis tables load when you select a file,
  so large folders can be browsed without loading everything into memory at once.
- **Load reporting.** Files that cannot be read are reported as warnings (missing
  file, unsupported type, or read error) rather than failing the whole folder
  load.

CloudScope's CZI and OIR support builds on file-format work by
[Christoph Gohlke](https://www.cgohlke.com/){target="_blank" rel="noopener"}.

## Sample data

To try CloudScope without your own files, load the sample datasets from the
[top header history menu](gui.md#top-header-and-loadsave-controls):

- **Load Velocity Sample Data** — OIR kymograph data for velocity analysis
- **Load Diameter Sample Data** — TIFF kymograph data for diameter analysis

See [Using the GUI](gui.md#getting-started-with-sample-data) for screenshots and
menu details.
