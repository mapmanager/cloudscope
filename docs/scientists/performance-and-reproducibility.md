# Performance and reproducibility

CloudScope separates visualization performance from scientific analysis. The GUI can use image pyramids to display only the resolution needed for the current view, while backend `acqstore` analysis operates on full-resolution image data.

Velocity and diameter analysis can use multiprocessing or multithreading where available. These acceleration paths are part of the backend analysis code, so scripts and GUI workflows can benefit from the same implementation.
