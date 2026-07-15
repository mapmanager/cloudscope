"""Modular top toolbar for :class:`SumIntensityPlotView` Edit F0 mode."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui


class SumIntensityPlotToolbar:
    """Edit F0 toolbar: Set Manual F0, Set Auto F0, and Close.

    Visible only while the plot view is in Edit F0 mode. Organized as:

    - Manual F0 readout (from the draggable H-line) + Set Manual F0
    - Percentile number + Set Auto F0
    - Close

    Args:
        on_set_manual_f0: Commit Manual F0 and run analysis.
        on_set_auto_f0: Commit Auto (percentile) F0 and run analysis.
        on_close: Exit Edit F0 without committing.
        on_percentile_changed: Optional preview callback when the percentile
            control changes (does not commit params).
    """

    def __init__(
        self,
        *,
        on_set_manual_f0: Callable[[], None],
        on_set_auto_f0: Callable[[], None],
        on_close: Callable[[], None],
        on_percentile_changed: Callable[[float], None] | None = None,
    ) -> None:
        self._on_set_manual_f0 = on_set_manual_f0
        self._on_set_auto_f0 = on_set_auto_f0
        self._on_close = on_close
        self._on_percentile_changed = on_percentile_changed
        self._root: ui.row | None = None
        self._pending_f0_label: ui.label | None = None
        self._percentile_control: ui.number | None = None
        self._set_manual_button: ui.button | None = None
        self._set_auto_button: ui.button | None = None
        self._visible = False
        self._actions_enabled = True

    @property
    def root(self) -> ui.row | None:
        """Return the built root row, or None before :meth:`build`."""
        return self._root

    @property
    def is_visible(self) -> bool:
        """Return whether the toolbar root is visible."""
        return self._visible

    def build(self) -> ui.row:
        """Build toolbar controls in the current NiceGUI slot.

        Returns:
            Root row element.
        """
        with ui.row().classes(
            "w-full shrink-0 items-center gap-3 flex-nowrap px-1"
        ) as self._root:
            with ui.row().classes("items-center gap-2 shrink-0"):
                self._pending_f0_label = ui.label("Manual F0: —").classes(
                    "text-sm opacity-80 whitespace-nowrap"
                )
                self._set_manual_button = ui.button(
                    "Set Manual F0",
                    on_click=self._on_set_manual_f0,
                ).props("dense")

            ui.separator().props("vertical").classes("h-8")

            with ui.row().classes("items-center gap-2 shrink-0"):
                self._percentile_control = (
                    ui.number(
                        label="Percentile",
                        value=20.0,
                        min=0.0,
                        max=100.0,
                        step=1.0,
                        format="%.1f",
                        on_change=self._on_percentile_control_changed,
                    )
                    .classes("w-28")
                    .props("dense")
                )
                self._set_auto_button = ui.button(
                    "Set Auto F0",
                    on_click=self._on_set_auto_f0,
                ).props("dense")

            ui.element("div").classes("flex-1 min-w-0")

            ui.button("Close", on_click=self._on_close).props("dense flat")
        self._apply_visibility()
        self._apply_actions_enabled()
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

    def enter_edit_f0_mode(self) -> None:
        """Show the Edit F0 toolbar.

        Returns:
            None.
        """
        self.set_visible(True)

    def exit_edit_f0_mode(self) -> None:
        """Hide the Edit F0 toolbar and clear the Manual F0 readout.

        Returns:
            None.
        """
        if self._pending_f0_label is not None:
            self._pending_f0_label.text = "Manual F0: —"
            self._pending_f0_label.update()
        self.set_visible(False)
        self.set_actions_enabled(True)

    def set_actions_enabled(self, enabled: bool) -> None:
        """Enable or disable Set Manual / Set Auto while a live run is in flight.

        Args:
            enabled: Whether Set buttons accept clicks.

        Returns:
            None.
        """
        self._actions_enabled = bool(enabled)
        self._apply_actions_enabled()

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

    def set_pending_f0(self, value: float) -> None:
        """Update the Manual F0 readout from the draggable H-line.

        Args:
            value: Current horizontal-line F0 position.

        Returns:
            None.
        """
        if self._pending_f0_label is None:
            return
        self._pending_f0_label.text = f"Manual F0: {value:.6g}"
        self._pending_f0_label.update()

    def _on_percentile_control_changed(self, event: object) -> None:
        """Forward percentile edits for Auto F0 preview.

        Args:
            event: NiceGUI number change event.

        Returns:
            None.
        """
        if self._on_percentile_changed is None:
            return
        value = getattr(event, "value", None)
        if value is None and self._percentile_control is not None:
            value = self._percentile_control.value
        if not isinstance(value, (int, float)):
            return
        self._on_percentile_changed(float(value))

    def _apply_visibility(self) -> None:
        """Apply root visibility.

        Returns:
            None.
        """
        if self._root is None:
            return
        self._root.set_visibility(self._visible)

    def _apply_actions_enabled(self) -> None:
        """Apply Set-button enabled state.

        Returns:
            None.
        """
        if self._set_manual_button is not None:
            self._set_manual_button.set_enabled(self._actions_enabled)
        if self._set_auto_button is not None:
            self._set_auto_button.set_enabled(self._actions_enabled)
        if self._percentile_control is not None:
            self._percentile_control.set_enabled(self._actions_enabled)

