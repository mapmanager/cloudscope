# End-user Recipes

Short step-by-step workflows for CloudScope analyses.

## Analysis recipes

Line scan kymograph analyses:

| Recipe | GUI | Description |
|---|---|---|
| [Velocity analysis](velocity-analysis.md) | Yes | *In vivo* blood flow velocity from a Radon-transform-based method |
| [Diameter analysis](diameter-analysis.md) | Yes | Vessel diameter measurement |
| [Sum intensity analysis](sum-intensity-analysis.md) | Yes | Functional fluorescence reporters (like GCaMP) from normalized line intensity |

Analyses that require a completed [velocity analysis](velocity-analysis.md) on the same
channel and ROI — see [Analyses from velocity](analyses-from-velocity/index.md):

| Recipe | GUI | Description |
|---|---|---|
| [Velocity event analysis](analyses-from-velocity/velocity-event-analysis.md) | Yes | Mark and analyze events on velocity results (inside the Velocity panel) |
| [Heart rate analysis](analyses-from-velocity/heart-rate-analysis.md) | No (notebook) | Heart rate from a velocity time series |

## See also

- [Using the GUI](../gui.md)
- [Pool plots](../pool-plots.md)
- [Saved file formats](../saved-files.md)
- [Data Scientist Guide](../../scientists/index.md) — parameters, notebooks, and programmatic workflows
