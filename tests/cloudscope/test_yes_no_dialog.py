"""Tests for reusable YesNoDialog callback routing."""

from cloudscope.views.dialogs.yes_no_dialog import YesNoDialog


def test_yes_no_dialog_no_and_cancel_share_callback() -> None:
    """No and Cancel should both invoke the negative callback path."""
    calls: list[str] = []
    dialog = YesNoDialog(
        title="Confirm",
        message="Proceed?",
        on_yes=lambda: calls.append("yes"),
        on_no=lambda: calls.append("no"),
    )

    dialog._handle_no()
    dialog._handle_no()
    dialog._handle_yes()

    assert calls == ["no", "no", "yes"]
