# Performance

CloudScope is optimized for interactive scientific image analysis.

## MVC/event-driven GUI updates

User interactions are propagated through application state and events. Views and widgets do not directly coordinate with one another; instead, controllers update state and emit events that linked views consume. This keeps the GUI synchronized while avoiding duplicated state.

## Image pyramids

The GUI can use image pyramids to display only what is needed for the current zoom level. This keeps visualization fast for large images. Backend analysis continues to use full-resolution image data from `acqstore`.

## Parallel analysis

Intensive analysis paths such as velocity and diameter analysis can use multiprocessing or multithreading where available. This is implemented in backend analysis functions so GUI workflows and scripting workflows use the same accelerated code paths.
