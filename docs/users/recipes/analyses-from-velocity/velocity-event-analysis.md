# Velocity event analysis

Velocity event analysis lets you **mark and analyze discrete events** on the velocity results
for a line scan kymograph ROI — for example, transient flow events visible in the kymograph or
velocity plot.

Events are managed in the **Velocity panel**, below the Radon velocity controls. There is no
separate left-toolbar icon for this workflow.

## Before you start

!!! warning "Run velocity analysis first"
    Complete [velocity analysis](../velocity-analysis.md) for the selected file, channel, and ROI.
    Event controls stay disabled until Radon velocity results exist for that selection.

## Run velocity event analysis in the GUI

1. Select the file, channel, and ROI in the file list.
2. Open the left toolbar and click **Velocity**.
3. Confirm Radon velocity results are present (run **Run Radon Analysis** if needed).
4. Scroll down in the Velocity panel to the **Events** section.
5. Use the event toolbar:
    - **Add** — click, then click and drag in the **2D plot** to set the event time range.
    - **Edit** — select an event in the table, click edit, then drag a new range in the plot.
    - **Delete** — remove the selected event.
    - **Select next** — move selection to the next event in the table.
    - **Cancel** — cancel an in-progress add or edit.
6. Toggle **Show events** to show or hide event overlays on the plot.
7. Adjust **Event parameters** if needed.
8. Click **Run/Reanalyze Events** to compute event statistics.
9. Review the event table and **Results** summary.
10. Use **Save** in the main toolbar to persist events and analysis state.

While adding or editing an event, CloudScope shows a notification asking you to click and drag
in the 2D plot to set the event range.

## Saved files

Event analysis state is stored in the acquisition **JSON sidecar** (`my_file.tif.json`) together
with velocity results and ROI data. There is no separate event CSV file.

## See also

- [Velocity analysis](../velocity-analysis.md)
- [Analyses from velocity](index.md)
- [Using the GUI](../../gui.md)
