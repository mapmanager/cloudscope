"""Preset-or-custom ``ui.select`` wiring for experiment metadata string fields.

NiceGUI 3.10.0 API source: ``nicegui/elements/select.py`` in the project venv.
Uses ``new_value_mode='add'`` with lazy option loading on ``popup-show`` and
``focus``.
"""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

GetFieldOptions = Callable[[str], list[str]]
OnCommit = Callable[[object | None], None]


def make_preset_str_select(
    *,
    field_name: str,
    label: str,
    widget_classes: str,
    get_field_options: GetFieldOptions | None,
    on_commit: OnCommit,
) -> ui.select:
    """Create a string select with preset options and free-form entry.

    Commit semantics (Option A from the experiment-metadata editor how-to):

    - Preset pick: ``on_value_change`` when the value is in the preset list.
    - Free-form: ``blur`` or ``keydown.enter`` after typing a new value.

    Args:
        field_name: Schema field name passed to ``get_field_options``.
        label: Control label.
        widget_classes: NiceGUI CSS classes for the control.
        get_field_options: Optional callback returning preset option strings.
        on_commit: Called with the committed value (may be ``None`` when cleared).

    Returns:
        Configured ``ui.select`` widget.
    """
    widget = ui.select(
        options=[],
        label=label,
        new_value_mode='add',
        clearable=True,
    ).classes(widget_classes)

    def _lazy_load_options(w: ui.select = widget) -> None:
        if get_field_options is None:
            return
        try:
            options = list(get_field_options(field_name) or [])
        except Exception:
            options = []
        current = w.value
        if current is not None and str(current).strip():
            cur_str = str(current).strip()
            if cur_str not in options:
                options = [cur_str] + options
        w.set_options(options, value=current)
        w.update()

    widget.on('popup-show', lambda _: _lazy_load_options())
    widget.on('focus', lambda _: _lazy_load_options())

    def _on_select_value_change(e, w: ui.select = widget) -> None:
        if e.value is None:
            return
        opts = (get_field_options(field_name) or []) if get_field_options else []
        if opts and str(e.value).strip() in [str(option).strip() for option in opts]:
            on_commit(e.value)
            try:
                w.run_method('blur')
            except Exception:
                pass

    widget.on_value_change(_on_select_value_change)
    widget.on('blur', lambda w=widget: on_commit(w.value))
    widget.on('keydown.enter', lambda w=widget: on_commit(w.value))
    return widget
