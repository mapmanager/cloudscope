# Decisions

- Use generic names: `TriggeredEventParams`, `TriggeredEvent`, and `analyze_triggered_events`.
- Use enums rather than string literals for direction, filtering, and status.
- Use reporter `onset.index` values as authoritative seeds.
- Include a pre-seed window for baseline and pre-event state.
- Do not require diameter derivative onset detection in version one.
- Limit extremum search with `post_search_window_points` and hard-limit all analysis at the next seed.
- Support `none`, median, and Savitzky–Golay filtering.
- Keep package-local tests under this package.
