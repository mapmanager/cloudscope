# 001 — Disconnect / reconnect handoff (planning)

**Status:** planning / handoff — **not implemented**  
**Type:** handoff ticket (implementation results belong in a follow-on ticket, e.g. `002_…`)  
**Branch:** `feature/fix-disconnect-reconnect-bug`  
**Worktree:** `/Users/cudmore/Sites/cloudscope-fix-disconnect`  
**Baseline commit:** `f3cef0f` — `before v1 implementation of 129_reconnect_plotly_refresh_report`

---

## How to use this file

1. Open Cursor on the worktree folder `cloudscope-fix-disconnect` (branch `feature/fix-disconnect-reconnect-bug`).
2. Start a **new chat** and reference this file: `@docs-dev/cursor_tickets/001_disconnect_reconnect_handoff.md`
3. Ask to **implement section 7** (first implementation ticket — Plotly reconnect fix).
4. After implementation, create **`002_…`** under `docs-dev/cursor_tickets/` with files changed, tests, and results (per `AGENTS.md`).

This file replaces cross-workspace chat history. Chat threads are not portable between Cursor workspaces.

---

## 1. Problem summary

CloudScope native desktop app (`./scripts/run app`, NiceGUI + pywebview). On WebSocket disconnect and **hard reconnect** (new browser client, full page rebuild), runtime state survives but **1D Plotly plots** often stay empty:

- **Acq analysis plot** (`AcqAnalysisPlotView`)
- **Sum intensity plot** (`SumIntensityPlotView`)

**Still works after bad reconnect:** file list tree selection, footer labels, primary kymograph image, clicks (not frozen).

**Workaround (confirmed):** select a different file, then return to the original selection → both plots populate.

**Triggers observed:** long macOS sleep, idle WebSocket timeout, `./scripts/run app` native. DevTools offline in `./scripts/run web` usually hard-reconnects successfully (plots OK) — same log shape as failures; difference is timing, not log pattern.

---

## 2. Bug classes

### 2a. Confirmed — empty 1D plots after hard reconnect (implement first)

| Symptom | Evidence |
|---|---|
| Plots empty after reconnect | Multiple user repros (sleep, idle) |
| State intact | Logs: `acq_image_list=loaded`, selection preserved |
| Primary image OK | 6× `full_image_png` after `build(complete)` |
| Not frozen | User can click; file-change workaround works |
| Log pattern | `client_disconnect` → new `client_id` → `build(start)` → `build(complete)` |

### 2b. Suspected — soft reconnect frozen UI (defer to ticket 003)

| Symptom | Evidence |
|---|---|
| UI looks populated, clicks do nothing | Reported earlier; **not** in recent logs |
| Hypothesis | `on_disconnect` → `on_hide()` unsubscribes views; same client reconnects without `build(start)` → no `on_show()` |

Recent user logs **always** include `build(start)` — those sessions are hard reconnect, not soft.

### 2c. Known behavior — layout chrome reset (defer)

On every hard `HomePage.build()`:

- Left toolbar: forced closed (`SplitterManager.value_for(LEFT_TOOLBAR)` + `LeftToolbarView.close_panel()`)
- Home file-list panel: collapsed peek (`_close_file_list_panel()`)
- Other splitters: restored from in-memory `app_config` drag positions

Cosmetic; not data loss. Defer unless requested.

### 2d. Separate — AG Grid warning #186 duplicate group keys

Console warning on file subtree refresh (`replace_group_rows`). Tree still works. Defer.

---

## 3. Architecture (reconnect)

| Layer | Survives hard reconnect? |
|---|---|
| `CloudScopeRuntime` / controllers / `HomePageState` | Yes (process-wide, `user_id='local'`) |
| NiceGUI widgets / views | No — rebuilt on each `home_page()` call |
| View hydration | `BaseView.on_show()` → `refresh_from_state()` + event subscriptions |
| Disconnect handler | `client.on_disconnect` → `on_hide()` on all views (unsubscribe) |

**Hard reconnect:** new `client_id`, `home_page()` runs `build()` again, views get `on_show()`.

**Soft reconnect (suspected bad path):** disconnect without subsequent `build(start)` — views stay unsubscribed.

---

## 4. Root cause — empty plots (locked)

### What works

- **Primary image:** `PrimaryImageView.build()` calls `after_build()` then `_refresh_raster_from_current_selection()`, which **schedules async** raster work (`_schedule_coro` → `_refresh_raster_async`). Log shows `full_image_png` **after** `build(complete)`.
- **Tree / footer:** read `app_state` in Python; no Plotly JS during build.

### What fails intermittently

- **Plot views:** `on_show()` → `refresh_from_state()` → `_refresh_plot()` → `PlotlyPlotWidget.set_series()` → `_push_series_data()` → `client.run_javascript()` **synchronously during `build()`**.
- New `ui.plotly(self._figure)` mounts with empty figure; JS push during build can race reconnecting client.
- **No `FileSelectionChanged`** republished after reconnect — plots get no second refresh unless user changes selection.

### User confirmation

After bad reconnect, clicking another file and back restores plots → `FileSelectionChanged` → `on_primary_selection_changed()` → `_refresh_plot()` **outside** build → works.

---

## 5. Log signature (good and bad reconnects look the same)

```
home_page [client_disconnect]     client_id=<old>
home_page [connect(before initialize_once)]   client_id=<new>
home_page reconnect: initialize_once skipped ...
home_page [build(start)]
home_page [build(complete)]
full_image_png × 6
```

Stale `client_disconnect` lines for **old** client IDs after a new client built are normal socket cleanup.

**Missing from logs today:** `FileSelectionChanged`, plot refresh, Plotly JS success/failure.

---

## 6. Follow-on tickets (document only — not in first implementation)

| Ticket | Title | Scope |
|---|---|---|
| **003** | Soft reconnect lifecycle | Instrument `on_connect` / `on_delete`; fix `on_hide()` on disconnect without matching rehydrate (A3/A4) |
| **004** | UI chrome persistence | Toolbar open/tab, file-list open, tree expansion in `app_config` |
| **005** | AG Grid #186 duplicate keys | `TreeWidget.replace_group_rows` transaction sync |

Numbering above is provisional; use next free `NNN` in `cursor_tickets/` when opening each ticket.

---

## 7. First implementation ticket (create as `002_…` when implementing)

**Goal:** Fix empty acq analysis + sum intensity plots after hard reconnect.

**Out of scope:** §2b soft reconnect, §2c layout chrome, §2d AG Grid, `ui.timer`, reload / `LoadPathIntent`, disconnect handler changes.

### B1 — Republish selection after reconnect build

| Item | Detail |
|---|---|
| **Where** | `src/cloudscope/pages/home_page.py` — after `page.build()` in `home_page()` |
| **When** | Only when `was_initialized` is True (reconnect; same flag used for existing reconnect log) |
| **What** | New public method on `HomePageController`: `republish_selection_from_state()` |
| **Implementation** | Delegate to existing `_publish_file_selection_after_lazy_data_loaded()` so lazy pixels stay consistent |

### B2 — Deferred plot refresh in both plot views

| Item | Detail |
|---|---|
| **Where** | `src/cloudscope/views/acq_analysis_plot_view.py`, `src/cloudscope/views/sum_intensity_plot_view.py` |
| **When** | End of each view's `build()`, after `after_build()` — every build (including first connect) |
| **What** | `_schedule_coro` with async wrapper: `await asyncio.sleep(0)` then `_refresh_plot()` |
| **Pattern** | Copy `_schedule_coro` from `PrimaryImageView` (module-local helper is fine) |
| **Forbidden** | `ui.timer` |

### B3 — Bake trace data into initial `ui.plotly` figure

**Skip** unless B1+B2 fail manual reconnect testing.

### Files expected to change

- `src/cloudscope/controllers/home_page_controller.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/acq_analysis_plot_view.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/cloudscope/` (controller + plot view tests)
- `docs-dev/cursor_tickets/002_reconnect_plotly_refresh_report.md` (after implementation)

### Unit tests

1. `republish_selection_from_state()` publishes `FileSelectionChanged` matching `state.selection` (mock event bus).
2. Plot views schedule deferred `_refresh_plot` after `build()` (patch `_schedule_coro` or plot widget).

### Manual acceptance

1. `./scripts/run app` — load sample data, select file with analyses.
2. Idle or sleep until reconnect (or reproduce known bad case).
3. After reconnect: both 1D plots show data **without** clicking another file.
4. File selection and primary image still correct.

### Test command

```bash
uv run pytest
```

---

## 8. Key source references

| File | Role |
|---|---|
| `src/cloudscope/pages/home_page.py` | Page route, `build()`, `on_disconnect`, diagnostic logging |
| `src/cloudscope/runtime.py` | `initialize_once()`, shared runtime |
| `src/cloudscope/controllers/home_page_controller.py` | Selection publish, `_publish_file_selection_changed` |
| `src/cloudscope/views/base_view.py` | `on_show()` / `on_hide()`, `refresh_from_state()` |
| `src/cloudscope/views/primary_image_view.py` | Reference: `_schedule_coro`, post-build async raster refresh |
| `src/cloudscope/views/acq_analysis_plot_view.py` | 1D velocity/diameter plot |
| `src/cloudscope/views/sum_intensity_plot_view.py` | Sum intensity plot |
| `src/nicewidgets/plotly_plot/widget.py` | `set_series()`, `_push_series_data()`, `_run_plotly_javascript()` |
| `src/cloudscope/views/splitter_manager.py` | Splitter values; left toolbar always closed on build |

---

## 9. Implementation results

**TBD** — record in `docs-dev/cursor_tickets/002_reconnect_plotly_refresh_report.md` after B1+B2 land.

---

## 10. Concerns or follow-ups

- Add optional INFO log in `_refresh_plot` (trace count) and ensure Plotly JS failures log at WARNING for easier log-only diagnosis.
- Ticket 003 should add `on_connect` / `on_delete` logging before changing disconnect behavior.
- Successful DevTools-offline reconnects do not disprove the plot bug — they often win the timing race.
