"""Reusable yes/no/cancel confirmation dialog for CloudScope views/controllers."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui


class YesNoDialog:
    """Reusable confirmation dialog with Yes, No, and Cancel actions.

    ``No`` and ``Cancel`` intentionally share the same callback path. This lets
    callers provide one safe fallback behavior while giving users an obvious
    cancel affordance that does not require reading the full dialog body.

    Args:
        title: Dialog title text.
        message: Dialog body text.
        yes_label: Label for the affirmative button.
        no_label: Label for the negative button.
        cancel_label: Label for the cancel button.
        on_yes: Callback invoked when the affirmative button is clicked.
        on_no: Optional callback invoked when either ``No`` or ``Cancel`` is
            clicked.
    """

    def __init__(
        self,
        *,
        title: str,
        message: str,
        yes_label: str = "Yes",
        no_label: str = "No",
        cancel_label: str = "Cancel",
        on_yes: Callable[[], None],
        on_no: Callable[[], None] | None = None,
    ) -> None:
        self.title = title
        self.message = message
        self.yes_label = yes_label
        self.no_label = no_label
        self.cancel_label = cancel_label
        self._on_yes = on_yes
        self._on_no = on_no
        self._dialog: ui.dialog | None = None

    def open(self) -> None:
        """Build and open the dialog.

        Returns:
            None.
        """
        with ui.dialog() as dialog, ui.card().classes("max-w-2xl"):
            self._dialog = dialog
            ui.label(self.title).classes("text-lg font-semibold")
            ui.label(self.message).classes("whitespace-pre-wrap text-sm")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(self.cancel_label, on_click=self._handle_no).props("flat")
                ui.button(self.no_label, on_click=self._handle_no).props("flat")
                ui.button(self.yes_label, on_click=self._handle_yes).props("color=negative")
        dialog.open()

    def _handle_yes(self) -> None:
        """Close the dialog and invoke the affirmative callback.

        Returns:
            None.
        """
        if self._dialog is not None:
            self._dialog.close()
        self._on_yes()

    def _handle_no(self) -> None:
        """Close the dialog and invoke the negative/cancel callback.

        Returns:
            None.
        """
        if self._dialog is not None:
            self._dialog.close()
        if self._on_no is not None:
            self._on_no()
