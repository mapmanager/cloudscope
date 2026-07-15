"""Modular top toolbar for :class:`SumIntensityPlotView`.

The toolbar is a thin NiceGUI surface so a future ticket can show/hide it or
host additional plot-local actions without rewriting Set F0 mode wiring.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui


class SumIntensityPlotToolbar:
    """Top toolbar for sum-intensity plot actions (Set F0 / Accept / Cancel).

    Args:
        on_set_f0: Invoked when the user clicks Set F0.
        on_accept: Invoked when the user accepts the pending Manual F0 value.
        on_cancel: Invoked when the user cancels Set F0 mode.
        on_compute_auto_f0: Invoked when the user recomputes Auto F0 from the
            toolbar percentile control.
    """

    def __init__(
        self,
        *,
        on_set_f0: Callable[[], None],
        on_accept: Callable[[], None],
        on_cancel: Callable[[], None],
        on_compute_auto_f0: Callable[[], None],
    ) -> None:
        self._on_set_f0 = on_set_f0
        self._on_accept = on_accept
        self._on_cancel = on_cancel
        self._on_compute_auto_f0 = on_compute_auto_f0
        self._root: ui.row | None = None
        self._idle_row: ui.row | None = None
        self._set_f0_row: ui.row | None = None
        self._auto_f0_label: ui.label | None = None
        self._pending_f0_label: ui.label | None = None
        self._percentile_control: ui.number | None = None
        self._visible = True
        self._set_f0_mode = False

    @property
    def root(self) -> ui.row | None:
        """Return the built root row, or None before :meth:`build`."""
        return self._root

    @property
    def is_visible(self) -> bool:
        """Return whether the toolbar root is visible."""
        return self._visible

    @property
    def is_set_f0_mode(self) -> bool:
        """Return whether Accept/Cancel chrome is shown."""
        return self._set_f0_mode

    def build(self) -> ui.row:
        """Build toolbar controls in the current NiceGUI slot.

        Returns:
            Root row element.
        """
        with ui.row().classes(
            "w-full shrink-0 items-center gap-2 flex-nowrap px-1"
        ) as self._root:
            with ui.row().classes("items-center gap-2") as self._idle_row:
                ui.button("Set F0", on_click=self._on_set_f0).props("dense outline")
            with ui.row().classes("items-center gap-2 flex-wrap") as self._set_f0_row:
                self._percentile_control = ui.number(
                    label="Percentile",
                    value=20.0,
                    min=0.0,
                    max=100.0,
                    step=1.0,
                    format="%.1f",
                ).classes("w-28").props("dense")
                ui.button(
                    "Compute auto F0",
                    on_click=self._on_compute_auto_f0,
                ).props("dense outline")
                self._auto_f0_label = ui.label("Auto F0: —").classes("text-sm opacity-80")
                self._pending_f0_label = ui.label("Manual F0: —").classes("text-sm opacity-80")
                ui.button("Accept", on_click=self._on_accept).props("dense")
                ui.button("Cancel", on_click=self._on_cancel).props("dense flat")
            self._set_f0_row.set_visibility(False)
        self._apply_visibility()
        return self._root

    def set_visible(self, visible: bool) -> None:
        """Show or hide the entire toolbar.

        Args:
            visible: Desired visibility.

        Returns:
            None.
        """
        self._visible = bool(visible)
        self._apply_visibility()

    def enter_set_f0_mode(self) -> None:
        """Show Accept/Cancel controls and hide the idle Set F0 control.

        Returns:
            None.
        """
        self._set_f0_mode = True
        self._sync_mode_rows()

    def exit_set_f0_mode(self) -> None:
        """Restore idle Set F0 chrome and clear F0 labels.

        Returns:
            None.
        """
        self._set_f0_mode = False
        if self._auto_f0_label is not None:
            self._auto_f0_label.text = "Auto F0: —"
            self._auto_f0_label.update()
        if self._pending_f0_label is not None:
            self._pending_f0_label.text = "Manual F0: —"
            self._pending_f0_label.update()
        self._sync_mode_rows()

    def set_baseline_percentile(self, value: float) -> None:
        """Set the percentile control value.

        Args:
            value: Baseline percentile in ``[0, 100]``.

        Returns:
            None.
        """
        if self._percentile_control is None:
            return
        self._percentile_control.value = float(value)
        self._percentile_control.update()

    def get_baseline_percentile(self) -> float:
        """Return the current percentile control value.

        Returns:
            Baseline percentile.

        Raises:
            RuntimeError: If the toolbar has not been built.
            TypeError: If the control value is not numeric.
        """
        if self._percentile_control is None:
            raise RuntimeError("toolbar has not been built")
        value = self._percentile_control.value
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"baseline percentile must be numeric, got {type(value).__name__}"
            )
        return float(value)

    def set_auto_f0(self, value: float) -> None:
        """Update the Auto F0 readout.

        Args:
            value: Percentile-estimated F0 value.

        Returns:
            None.
        """
        if self._auto_f0_label is None:
            return
        self._auto_f0_label.text = f"Auto F0: {value:.6g}"
        self._auto_f0_label.update()

    def set_pending_f0(self, value: float) -> None:
        """Update the pending Manual F0 readout.

        Args:
            value: Current horizontal-line F0 position.

        Returns:
            None.
        """
        if self._pending_f0_label is None:
            return
        self._pending_f0_label.text = f"Manual F0: {value:.6g}"
        self._pending_f0_label.update()

    def _sync_mode_rows(self) -> None:
        """Sync idle vs Set F0 row visibility from mode state.

        Returns:
            None.
        """
        if self._idle_row is not None:
            self._idle_row.set_visibility(not self._set_f0_mode)
        if self._set_f0_row is not None:
            self._set_f0_row.set_visibility(self._set_f0_mode)

    def _apply_visibility(self) -> None:
        """Apply root visibility.

        Returns:
            None.
        """
        if self._root is None:
            return
        self._root.set_visibility(self._visible)
