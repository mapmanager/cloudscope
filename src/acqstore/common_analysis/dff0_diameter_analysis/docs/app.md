# App

Run from the repository root:

```bash
uv run python -m acqstore.common_analysis.dff0_diameter_analysis.app.main
```

The app rebuilds each Plotly figure from scratch when `Replot` is pressed. It is intentionally independent of the CloudScope GUI and may use Plotly updates or full reconstruction freely.
