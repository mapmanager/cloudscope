# Ticket 018 — Move `visible_file_ids_provider` onto `app_state`

## Summary

The "visible/filtered/sorted file ids" provider that powers the **Batch
analyze visible rows** buttons in `VelocityAnalysisView` and
`DiameterAnalysisView` previously had to be threaded through
`LeftToolbarView` as a constructor argument and forwarded into both child
views. `LeftToolbarView` was a pure pass-through for this value, which was a
wiring smell.

This ticket relocates the provider onto `HomePageState` and has the analysis
views read it directly. `LeftToolbarView` no longer references the provider
in any way. `BatchAnalysisDialog` is unchanged and remains a small, dumb,
self-contained confirmation widget.

## Files changed

- `src/cloudscope/controllers/home_page_controller.py`
  - Added `Awaitable` / `Callable` imports and `field` from `dataclasses`.
  - Added a new field on `HomePageState`:
    `visible_file_ids_provider: Callable[[], Awaitable[list[str]]] | None`
    defaulting to ``None``. Docstring updated.
- `src/cloudscope/pages/home_page.py`
  - After constructing `file_list_panel = AcqImageListTableView(...)`,
    assigns `app_state.visible_file_ids_provider =
    file_list_panel.get_displayed_file_ids` once. No other changes.
- `src/cloudscope/views/left_toolbar_view.py`
  - Removed the `visible_file_ids_provider` constructor parameter.
  - Removed the two forwarding lines that passed the provider into
    `VelocityAnalysisView` and `DiameterAnalysisView`.
  - Removed the now-unused `Awaitable` import.
  - Updated class docstring to point at `app_state`.
- `src/cloudscope/views/velocity_analysis_view.py`
  - Removed the `visible_file_ids_provider` constructor parameter and its
    `self._visible_file_ids_provider` attribute.
  - Added a private helper `_visible_file_ids_provider()` that returns
    `getattr(self.app_state, "visible_file_ids_provider", None)` (safe when
    `app_state` is `None`).
  - `_on_batch_clicked` snapshots the provider via the helper, then calls
    `await provider()`.
  - `_refresh_run_button` gates the batch button on
    `self._visible_file_ids_provider() is not None`.
  - Class docstring updated to point at `app_state`.
- `src/cloudscope/views/diameter_analysis_view.py`
  - Same set of changes as `velocity_analysis_view.py`.

## Implementation notes

- `HomePageState` uses `@dataclass(slots=True)`, so the new field is declared
  with `field(default=None)` to remain compatible with slotted dataclasses.
- The helper is defined as `_visible_file_ids_provider(self) -> Callable[...,
  Awaitable[list[str]]] | None`. It deliberately uses `getattr` with a
  `None` default so unit tests that pass non-`HomePageState` fakes for
  `app_state` (or `None`) keep working unchanged.
- `HomePage.build()` sets the provider once. The bound method
  `AcqImageListTableView.get_displayed_file_ids` is `async`, defined on the
  view, and already returns `[]` safely when the table is not yet built.
  Set-once timing is fine because the provider is only read at user click
  time and during selection-dependent button refresh, both of which happen
  after the file table has been built.
- `BatchAnalysisDialog` is **unchanged**. It remains a constructor-injected
  dumb widget with a simple, fully-typed surface (`file_ids`, `channel`,
  `roi_id`, `on_run`). This preserves its standalone testability and avoids
  coupling the dialog to app state.
- `LeftToolbarView` no longer participates in this wiring at all, eliminating
  the pass-through smell that motivated the ticket.

## Tests added or modified

None. The refactor preserves all public behavior of the analysis views and
the toolbar:

- The batch button is enabled exactly when there is a valid file/channel/ROI
  selection *and* a registered provider on `app_state`.
- The "Visible file-table rows are not available" toast still fires when no
  provider has been registered.
- Existing tests in `tests/cloudscope/test_velocity_analysis_view.py`,
  `tests/cloudscope/test_diameter_analysis_view.py`,
  `tests/cloudscope/test_left_toolbar_view.py`, and
  `tests/cloudscope/test_file_list_view.py` cover the surfaces touched. No
  test references the now-removed `_visible_file_ids_provider` instance
  attribute, the old constructor parameter, or `LeftToolbarView`'s old
  `visible_file_ids_provider` kwarg.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_analysis_view.py \
              tests/cloudscope/test_diameter_analysis_view.py \
              tests/cloudscope/test_left_toolbar_view.py \
              tests/cloudscope/test_file_list_view.py \
              tests/cloudscope/test_home_page.py -q
uv run pytest -q
```

## Test results

Targeted (five files exercising the refactored surfaces):

```
39 passed in 1.00s
```

Full suite:

```
739 passed, 3 warnings in 2.72s
```

The three warnings (`PytestCollectionWarning` for `TestEvent` and two
`All-NaN slice` `RuntimeWarning`s from `raster_service.py`) are pre-existing
and unrelated to this ticket.

## Concerns or follow-ups

- The provider is set once in `HomePage.build()` and never cleared. That
  matches the lifecycle of `HomePageState` itself; if a future page needed to
  swap the file-list view, that page would need to update the provider on
  its own state.
- The analysis views still gate their batch button on
  `provider is not None`. If a future requirement wants to disable the
  button purely on the absence of *visible rows* rather than the absence of
  a *provider*, that would require an additional state field or a cheap sync
  count method on the file-table view. Not introduced here.
- `BatchAnalysisDialog` is intentionally not touched. It stays standalone
  with a primitive-only constructor surface and a callback. If the dialog
  later needs richer app-state awareness, that should be a separate ticket
  with explicit reasons.
