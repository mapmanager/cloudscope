# CloudScope diameter analysis glue

This note describes the small API surface CloudScope needs after acqstore adds a diameter analysis.
It is intentionally glue-level only: acqstore owns the science and nicewidgets owns rendering.

## Boundary

- acqstore owns diameter analysis computation, storage, and analysis result access.
- cloudscope consumes app state and acqstore analysis results, then adapts them to nicewidgets overlays.
- nicewidgets draws `PlotlyTraceOverlay` objects and does not know about diameter analysis.

No acqstore code should import nicewidgets.

## Analysis identity

Diameter analysis should follow the existing analysis identity pattern:

```text
selected AcqImage
+ selected channel
+ selected roi_id
+ AnalysisKind.DIAMETER
```

This matches the existing runtime model used by analysis views: views consume current selection from app state, build an analysis key from analysis kind/channel/ROI, and then read the matching analysis result from the selected acquisition image.

## acqstore result API needed by CloudScope

CloudScope needs ``BaseAnalysis.get_overlay_traces()`` returning ROI-local physical
coordinates for the selected `(acq_image, channel, roi_id)` diameter analysis.

A neutral acqstore DTO is preferred, for example:

```python
@dataclass(frozen=True, slots=True)
class AnalysisOverlayTraceData:
    trace_id: str
    x: tuple[float, ...]
    y: tuple[float, ...]
    color: str | None = None
    name: str | None = None
    visible: bool = True
```

Required semantics (ROI-local; see `docs/acqstore_kymograph_axes.md`):

- `trace_id` is stable for the analysis trace.
- `x` is time in seconds from the ROI's first analyzed row.
- `y` is space in microns from the ROI's first analyzed column.
- `len(x) == len(y)`.
- Empty tuples are valid when no overlay exists.
- acqstore does not return nicewidgets `PlotlyTraceOverlay`.

CloudScope translates ROI-local `(x, y)` to full-image Plotly coordinates in
`primary_image_view.roi_local_traces_to_plotly_overlays()` using
`RectROI.bounds` and `RasterGridSpec` (`plot-x = dim0`, `plot-y = dim1`).

If the diameter analysis can produce multiple overlays later, the getter can return a sequence of DTOs. For the first implementation, one overlay trace is enough unless the analysis design requires otherwise.

## CloudScope consumption

CloudScope should convert acqstore DTOs to nicewidgets overlays at the view boundary:

```python
PlotlyTraceOverlay(
    trace_id=data.trace_id,
    x=data.x,
    y=data.y,
    color=data.color,
    name=data.name,
    visible=data.visible,
)
```

The view should call:

```python
viewer.set_trace_overlays(overlays)
```

or clear when the selected analysis is unavailable:

```python
viewer.clear_trace_overlays()
```

## Refresh triggers

Diameter overlays should refresh when:

- diameter analysis completes for the selected `(acq_image, channel, roi_id)`;
- selected acquisition image changes;
- selected channel changes;
- selected ROI changes;
- ROI edit/delete invalidates or removes the current analysis result.

For image/channel/ROI changes that also reload the raster image, CloudScope should avoid two browser pushes. Update overlay state before the full raster refresh when possible, then let the full raster refresh carry the overlay state. For analysis-completion updates where the raster image is unchanged, use the overlay-only viewer API.

## Non-goals

- Do not add diameter analysis logic to CloudScope.
- Do not add diameter concepts to nicewidgets.
- Do not add axis labels to trace overlays; the raster image/grid owns axis labels and scaling.
- Do not make `AcqAnalysisPlotView` polymorphic until one-analysis-per-ROI is enforced.
