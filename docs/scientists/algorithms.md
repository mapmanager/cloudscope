# Algorithms and results

CloudScope algorithms are implemented in `acqstore` so they can be used from the desktop GUI, browser GUI, Python scripts, and notebooks. The GUI is an interface to the same scientific analysis code used by scripted workflows.

## Velocity analysis

Velocity analysis estimates motion or propagation speed from image data within a selected acquisition, channel, and ROI. The current implementation focuses on ROI-based analysis so results are tied to a specific region of the acquisition.

### Velocity parameters

Velocity parameters control scientific detection behavior. These include algorithm-specific choices such as the selected channel, ROI, analysis window, preprocessing options, detection thresholds, and algorithm settings.

Execution settings such as cancellation, progress reporting, multiprocessing, or multithreading are separate from scientific detection parameters. They may affect runtime, but they should not change the scientific meaning of the result.

### Velocity results

Velocity results should document the measured value, units, selected file, channel, ROI, algorithm parameters, and any table or trace data produced by the analysis. Results can be inspected in the GUI or accessed from scripts using the same `acqstore` analysis objects.

## Diameter analysis

Diameter analysis estimates diameter or width-related measurements from image data within a selected acquisition, channel, and ROI. As with velocity analysis, the scientific implementation lives in `acqstore` and is shared by GUI and scripted workflows.

### Diameter parameters

Diameter parameters define the detection and measurement behavior. These include selected data, ROI, channel, thresholding or profile settings, and algorithm-specific choices used to estimate diameter.

Performance settings are treated separately from scientific parameters. CloudScope can use multiprocessing or multithreading where available to save time, while preserving the same analysis API for GUI and script users.

### Diameter results

Diameter results should include the measured diameter values, units, acquisition context, ROI context, parameter set, and output table or plot data. The goal is that the same data and parameters produce the same results whether analysis is launched from the GUI, notebook, or script.

## Documentation status

This page is the narrative overview for algorithms, parameters, and results. The detailed API reference is generated from Google-style docstrings in `acqstore`, and executable examples are provided in the notebook section.
