# Supported file formats

CloudScope supports native loading of commercial proprietary microscopy formats and open scientific image formats.

## Commercial formats

- Olympus / Evident `.oir`
- Zeiss `.czi`

## Open formats

- TIFF `.tif`
- OME-Zarr `.ome.zarr`

Support for these formats is provided through the `acqstore` backend so the same file-loading behavior is available to the desktop GUI, browser GUI, notebooks, and Python scripts.

## Acknowledgement

Support for commercial microscopy formats builds on the scientific Python ecosystem. CloudScope gratefully acknowledges [Christoph Gohlke](https://www.cgohlke.com/){target="_blank" rel="noopener"} for long-standing work on microscopy and scientific file-format tooling.
