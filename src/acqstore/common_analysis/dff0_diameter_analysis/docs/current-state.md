# Current State

Implemented:

- generic seeded-event engine;
- pre-seed baseline and trend measurements;
- next-seed truncation;
- independent post-seed extremum search limit;
- extremum, amplitude, timing, slope, recovery, and AUC;
- enums and serialization;
- sidecar and AcqImage adapters;
- Plotly overview, event, and metric-versus-time plots;
- standalone NiceGUI app;
- package-local tests.

Development examples:

- `220110n_0005.tif`, channel 0, ROI 1;
- `220110n_0020.tif`, channel 0, ROI 1;
- `220110n_0022.tif`, channel 0, ROI 1;
- `220110n_0023.tif`, channel 0, ROI 1.

Next scientific work should inspect event measurements across all four recordings before adding response-onset detection or continuous cross-correlation.
