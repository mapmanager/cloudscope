# End-user Recipes

Short workflows for common CloudScope tasks.

## General workflows

### Open data

1. Launch CloudScope.
2. Use the load/open controls in the top toolbar.
3. Select a supported image file or folder.
4. Choose an image in the file list.
5. Inspect the image in the main viewer.

Supported formats include `.oir`, `.czi`, `.tif`, and `.ome.zarr`.

### Load sample data

Use the CloudScope sample-data menu item to fetch example data from the
[cloudscope-data Repository](https://github.com/mapmanager/cloudscope-data){target="_blank" rel="noopener"}.

Sample data is the recommended first step when trying the application or checking a
[fresh installation](../install.md).

### Export and saved files

CloudScope saves sidecar files next to the source image file.

For a source file named `my_file.tif`, saved files may include:

```text
my_file.tif.json
my_file.tif.radon_velocity.csv
my_file.tif.diameter.csv
```

The JSON sidecar stores CloudScope state, ROIs, metadata, and analysis summaries that do not
have a dedicated CSV file. CSV files store tabular outputs for velocity and diameter analyses.

Use **Save** in the main toolbar to persist your work.

## Analysis recipes

Line scan kymograph analyses:

| Recipe | GUI | Description |
|---|---|---|
| [Velocity analysis](velocity-analysis.md) | Yes | Blood flow velocity from a Radon-transform-based method |
| [Diameter analysis](diameter-analysis.md) | Yes | Vessel diameter from line scan kymographs |

Analyses that require a completed [velocity analysis](velocity-analysis.md) on the same
channel and ROI — see [Analyses from velocity](analyses-from-velocity/index.md):

| Recipe | GUI | Description |
|---|---|---|
| [Velocity event analysis](analyses-from-velocity/velocity-event-analysis.md) | Yes | Mark and analyze events on velocity results (inside the Velocity panel) |
| [Heart rate analysis](analyses-from-velocity/heart-rate-analysis.md) | No (notebook) | Heart rate from a velocity time series |

## See also

- [Using the GUI](../gui.md)
- [Data Scientist Guide](../../scientists/index.md) — parameters, notebooks, and programmatic workflows
