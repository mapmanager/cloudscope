# Notebook Workflows

CloudScope includes notebook examples for users who want to load data, inspect arrays, run analysis, and view results from Python.

The notebooks are rendered in the documentation site and are not currently executed in CI.

## Available notebooks

- [Load and Plot Image](../notebooks/load-and-plot-image.ipynb)
- [Velocity Analysis](../notebooks/velocity-analysis.ipynb)
- [Diameter Analysis](../notebooks/diameter-analysis.ipynb)
- [Kymograph Reference Images](../notebooks/kymograph-reference-image.ipynb)
- [Heart Rate Analysis](../notebooks/heart-rate-analysis.ipynb) — see also the [End User heart rate recipe](../users/recipes/analyses-from-velocity/heart-rate-analysis.md) (no GUI yet)
- [Heart Rate Batch Analysis](../notebooks/heart-rate-batch-analysis.ipynb)

## Plotting

CloudScope runtime code does not depend on Matplotlib because Matplotlib can slow down NiceGUI startup and runtime behavior. Matplotlib is included only in the documentation dependency group for examples and notebooks.

Notebook examples may use Matplotlib for simple inline plots and Plotly where interactive visualization is useful.
