# Reproducibility model

CloudScope is designed so that desktop GUI workflows, browser GUI workflows, Python scripts, and notebooks all use the same `acqstore` backend.

This is important because scientific analysis should not depend on how the user starts the workflow. The same acquisition objects, ROI data, analysis algorithms, parameter handling, and result-generation code are shared across interfaces.

This design reduces divergence, simplifies validation, and makes it easier to compare GUI-driven results with scripted analysis.

## Versioned releases

Official CloudScope releases are tied to versioned source code and released desktop/web artifacts. A published release provides a reproducible reference point for scientific analysis: users can record the version used for an experiment, return to the same source and application build later, and still allow active development to move forward in future releases.

When writing methods sections, notebooks, or lab records, record the CloudScope version together with the input data, ROIs, analysis parameters, and exported results.
