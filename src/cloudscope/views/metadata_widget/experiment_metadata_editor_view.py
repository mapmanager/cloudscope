"""Per-field experiment metadata editor for the CloudScope left toolbar."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.metadata import ExperimentMetadata
from acqstore.schema import FieldSchema, SchemaDefinition, ValueType

from cloudscope.views.metadata_widget.preset_select import GetFieldOptions, make_preset_str_select

OnFieldCommit = Callable[[str, object], None]
NOTE_FIELD_NAME = 'note'


class ExperimentMetadataEditorView:
    """Schema-driven experiment metadata form with per-field commit.

    Widgets are built once inside ``build()``. Selection changes sync values
    via ``set_selected_acq_image`` without rebuilding the control tree.

    Args:
        on_field_commit: Called with ``(field_name, value)`` when the user
            commits one editable field.
        get_field_options: Optional callback returning preset strings for
            combobox string fields (excluding ``note``).
    """

    def __init__(
        self,
        *,
        on_field_commit: OnFieldCommit,
        get_field_options: GetFieldOptions | None = None,
    ) -> None:
        self._on_field_commit = on_field_commit
        self._get_field_options = get_field_options
        self._schema = ExperimentMetadata().get_schema()
        self._widgets: dict[str, ui.input | ui.number | ui.select | ui.checkbox] = {}
        self._readonly_labels: dict[str, ui.label] = {}
        self._read_only_fields: dict[str, FieldSchema] = {}
        self._select_field_names: set[str] = set()
        self._current_acq_image: AcqImage | None = None
        self._suppress_field_change = False
        self._last_committed_values: dict[str, str] = {}
        self._root: ui.column | None = None

    def build(self, parent: ui.element | None = None) -> ui.column:
        """Build the editor inside an optional NiceGUI parent.

        Args:
            parent: Optional container element.

        Returns:
            Root column for this editor.
        """
        self._widgets = {}
        self._readonly_labels = {}
        self._read_only_fields = {}
        self._select_field_names = set()

        def _build_inner() -> ui.column:
            with ui.column().classes('w-full gap-2') as root:
                self._root = root
                ui.label(ExperimentMetadata.display_section_title).classes('text-lg font-bold')
                visible_schema = [field for field in self._schema.fields if field.visible]
                self._read_only_fields = {
                    field.name: field for field in visible_schema if not field.editable
                }
                with ui.grid(columns=2).classes('w-full gap-2'):
                    for group_name, field_list in _group_visible_fields(self._schema):
                        if group_name is not None:
                            with ui.element('div').classes('col-span-2 w-full'):
                                ui.separator()
                                ui.label(str(group_name)).classes('font-semibold opacity-70')
                        for field in field_list:
                            self._build_field(field)
            return root

        if parent is not None:
            with parent:
                return _build_inner()
        return _build_inner()

    def set_selected_acq_image(self, acq_image: AcqImage | None) -> None:
        """Sync widgets from the selected file's experiment metadata.

        Args:
            acq_image: Selected acquisition image, or ``None`` to clear.
        """
        self._current_acq_image = acq_image
        self._suppress_field_change = True
        try:
            if acq_image is None:
                self._clear_widget_values()
                return
            section = acq_image.get_metadata_section(ExperimentMetadata.metadata_section_id)
            values = section.get_values()
            for field_name, widget in self._widgets.items():
                if field_name not in values:
                    continue
                raw = values[field_name]
                normalized = _normalize_committed_value(raw)
                if field_name in self._select_field_names:
                    value_str = '' if raw is None else str(raw)
                    options = (
                        list(self._get_field_options(field_name) or [])
                        if self._get_field_options is not None
                        else []
                    )
                    if normalized and normalized not in options:
                        options = [normalized] + options
                    widget.set_options(options, value=value_str or None)
                elif isinstance(widget, ui.number):
                    widget.set_value(raw)
                elif isinstance(widget, ui.checkbox):
                    widget.set_value(bool(raw))
                else:
                    widget.set_value('' if raw is None else str(raw))
                self._last_committed_values[field_name] = normalized
            for field_name, field in self._read_only_fields.items():
                label = self._readonly_labels.get(field_name)
                if label is None:
                    continue
                raw = values.get(field.name, '')
                display = '' if raw is None else str(raw)
                label.text = display
                label.update()
                self._last_committed_values[field_name] = display.strip()
        finally:
            self._suppress_field_change = False

    def clear(self) -> None:
        """Clear the current record and reset widget values."""
        self.set_selected_acq_image(None)

    def _clear_widget_values(self) -> None:
        """Reset widgets without changing the current record reference."""
        for field_name, widget in self._widgets.items():
            if field_name in self._select_field_names:
                widget.set_options([], value=None)
            elif isinstance(widget, ui.number):
                widget.set_value(None)
            elif isinstance(widget, ui.checkbox):
                widget.set_value(False)
            else:
                widget.set_value('')
            self._last_committed_values[field_name] = ''
        for field_name, label in self._readonly_labels.items():
            label.text = ''
            label.update()
            self._last_committed_values[field_name] = ''

    def _build_field(self, field: FieldSchema) -> None:
        label = _label_for_field(field)
        widget_classes = 'w-full'

        if not field.editable:
            with ui.element('div').classes('col-span-2 w-full'):
                ui.label(label).classes('text-xs text-gray-500')
                value_label = ui.label('').classes('text-sm')
            self._readonly_labels[field.name] = value_label
            return

        if field.value_type is ValueType.STR and field.name != NOTE_FIELD_NAME:
            widget = make_preset_str_select(
                field_name=field.name,
                label=label,
                widget_classes=widget_classes,
                get_field_options=self._get_field_options,
                on_commit=lambda value, name=field.name: self._on_field_change(name, value),
            )
            self._select_field_names.add(field.name)
        elif field.value_type is ValueType.STR:
            widget = ui.input(label=label).classes(widget_classes)
            widget.on('blur', lambda w=widget, name=field.name: self._on_field_change(name, w.value))
            widget.on(
                'keydown.enter',
                lambda w=widget, name=field.name: self._on_field_change(name, w.value),
            )
        elif field.value_type is ValueType.INT:
            widget = ui.number(label=label, precision=0).classes(widget_classes)
            widget.on('blur', lambda w=widget, name=field.name: self._on_field_change(name, w.value))
            widget.on(
                'keydown.enter',
                lambda w=widget, name=field.name: self._on_field_change(name, w.value),
            )
        elif field.value_type is ValueType.FLOAT:
            widget = ui.number(label=label).classes(widget_classes)
            widget.on('blur', lambda w=widget, name=field.name: self._on_field_change(name, w.value))
            widget.on(
                'keydown.enter',
                lambda w=widget, name=field.name: self._on_field_change(name, w.value),
            )
        elif field.value_type is ValueType.BOOL:
            widget = ui.checkbox(text=label)
            widget.on(
                'update:model-value',
                lambda e, name=field.name: self._on_field_change(name, e.args),
            )
        else:
            widget = ui.input(label=label).classes(widget_classes)
            widget.on('blur', lambda w=widget, name=field.name: self._on_field_change(name, w.value))
            widget.on(
                'keydown.enter',
                lambda w=widget, name=field.name: self._on_field_change(name, w.value),
            )

        self._widgets[field.name] = widget

    def _on_field_change(self, field_name: str, value: object | None) -> None:
        if self._current_acq_image is None:
            return
        if self._suppress_field_change:
            return

        normalized = _normalize_committed_value(value)
        if normalized == self._last_committed_values.get(field_name, ''):
            return

        self._on_field_commit(field_name, value)
        self._last_committed_values[field_name] = normalized


def _normalize_committed_value(value: object | None) -> str:
    """Return a normalized string used to detect duplicate commits."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _label_for_field(field: FieldSchema) -> str:
    if field.unit:
        return f'{field.display_name} ({field.unit})'
    return field.display_name


def _group_visible_fields(schema: SchemaDefinition) -> list[tuple[str | None, list[FieldSchema]]]:
    groups: list[tuple[str | None, list[FieldSchema]]] = []
    for field in schema.fields:
        if not field.visible:
            continue
        group_name = field.group
        for existing_name, group_fields in groups:
            if existing_name == group_name:
                group_fields.append(field)
                break
        else:
            groups.append((group_name, [field]))
    return groups
