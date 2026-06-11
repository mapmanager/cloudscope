# End-user Recipes

This page collects short workflows for common CloudScope tasks.

## Open data

1. Launch CloudScope.
2. Use the load/open controls in the top toolbar.
3. Select a supported image file or folder.
4. Choose an image in the file list.
5. Inspect the image in the main viewer.

Supported formats include `.oir`, `.czi`, `.tif`, and `.ome.zarr`.

## Load sample data

Use the CloudScope sample-data menu item to fetch example data from the [cloudscope-data Repository](https://github.com/mapmanager/cloudscope-data){target="_blank" rel="noopener"}.

Sample data is the recommended first step when trying the application or checking a fresh installation.

## Run blood flow velocity analysis

Velocity analysis estimates blood flow velocity from line scan kymographs using a Radon-transform-based method.

1. Load a line scan kymograph.
2. Select the file in the file list.
3. Select or create an ROI covering the region to analyze.
4. Open the velocity analysis panel.
5. Review the detection parameters.
6. Run the analysis.
7. Inspect the summary and tabular results.
8. Save results.

## Run diameter analysis

Diameter analysis estimates vessel diameter from line scan kymographs.

1. Load a line scan kymograph.
2. Select the file in the file list.
3. Select or create an ROI covering the vessel region.
4. Open the diameter analysis panel.
5. Review the detection parameters.
6. Run the analysis.
7. Inspect the summary and quality-control values.
8. Save results.

## Export results

CloudScope saves sidecar files next to the source image file.

For a source file named `my_file.tif`, saved files may include:

```text
my_file.tif.json
my_file.tif.radon_velocity.csv
my_file.tif.diameter.csv
```

The JSON sidecar stores CloudScope state. CSV files store analysis-specific tabular results.
