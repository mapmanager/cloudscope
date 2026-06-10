# Notebooks

Starter notebooks are rendered into this documentation site for exploration. For phase 1, notebooks are documentation examples only and are not executed in CI.

Start with:

- Load and plot image
- Velocity analysis
- Diameter analysis

The first notebook intentionally does only three things: load a file, get image data, and plot the image with Matplotlib.

!!! note "Matplotlib dependency"
    Matplotlib is included only in the documentation dependency group for notebooks and examples. It is intentionally not part of the CloudScope runtime dependencies because it can slow down NiceGUI startup and runtime behavior.
