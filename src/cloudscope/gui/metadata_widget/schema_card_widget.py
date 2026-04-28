"""NiceGUI card driven by an ``acqstore`` ``SchemaDefinition`` and values mapping."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from nicegui import ui

from acqstore.schema import FieldSchema, SchemaDefinition, ValueType


class SchemaCardWidget:
    """Schema-driven NiceGUI card: labels, inferred controls, and Apply."""

    def __init__(
        self,
        title: str,
        schema: SchemaDefinition,
        values: Mapping[str, object],
        *,
        on_apply: Callable[[dict[str, object]], None] | None = None,
        show_apply_button: bool = True,
    ) -> None:
        self._title = title
        self._schema = schema
        self._values = dict(values)
        self._on_apply = on_apply
        self._show_apply_button = show_apply_button
        self._card: ui.card | None = None
        self._controls: dict[str, Any] = {}

    def build(self, parent: ui.element | None = None) -> ui.card:
        """Build and return the card (optionally inside ``parent``)."""
        self._controls.clear()
        if parent is not None:
            with parent:
                return self._build_inner()
        return self._build_inner()

    def _build_inner(self) -> ui.card:
        with ui.card().classes('w-full') as card:
            self._card = card
            ui.label(self._title).classes('text-lg font-bold')
            for group_name, field_list in self._group_visible_fields():
                if group_name is not None:
                    ui.separator()
                    ui.label(str(group_name)).classes('text-sm font-semibold opacity-70')
                for field in field_list:
                    raw = self._values.get(field.name, field.default)
                    self._build_field(field, raw)
            if self._show_apply_button and self._has_editable_fields() and self._on_apply is not None:
                ui.button('Apply', on_click=self._apply).props('color=primary')
        return card

    def get_patch(self) -> dict[str, object]:
        """Return current values for visible editable fields only."""
        patch: dict[str, object] = {}
        for field in self._schema.fields:
            if not field.visible or not field.editable:
                continue
            control = self._controls.get(field.name)
            if control is None:
                continue
            patch[field.name] = control.value
        return patch

    def update_values(self, values: Mapping[str, object]) -> None:
        """Update bound values and refresh editable controls."""
        self._values = dict(values)
        for name, control in self._controls.items():
            if name in self._values:
                control.value = self._values[name]
                control.update()

    def _apply(self) -> None:
        if self._on_apply is not None:
            self._on_apply(self.get_patch())

    def _has_editable_fields(self) -> bool:
        return any(f.visible and f.editable for f in self._schema.fields)

    def _group_visible_fields(self) -> list[tuple[str | None, list[FieldSchema]]]:
        groups: list[tuple[str | None, list[FieldSchema]]] = []
        for field in self._schema.fields:
            if not field.visible:
                continue
            g = field.group
            for group_name, group_fields in groups:
                if group_name == g:
                    group_fields.append(field)
                    break
            else:
                groups.append((g, [field]))
        return groups

    def _label_for_field(self, field: FieldSchema) -> str:
        if field.unit:
            return f'{field.display_name} ({field.unit})'
        return field.display_name

    def _stringify_readonly(self, value: object) -> str:
        if value is None:
            return ''
        return str(value)

    def _build_field(self, field: FieldSchema, value: object) -> None:
        if not field.editable:
            ui.label(self._label_for_field(field)).classes('text-xs text-gray-500')
            ui.label(self._stringify_readonly(value)).classes('text-sm')
            return

        if field.choices is not None:
            opts = list(field.choices)
            control = ui.select(
                label=self._label_for_field(field),
                options=opts,
                value=value if value in opts else (opts[0] if opts else None),
            ).classes('w-full')
            self._controls[field.name] = control
            return

        if field.value_type is ValueType.BOOL:
            control = ui.checkbox(text=self._label_for_field(field), value=bool(value))
            self._controls[field.name] = control
            return

        if field.value_type is ValueType.INT:
            num_val: int | None
            if value is None or value == '':
                num_val = None
            else:
                num_val = int(value)  # type: ignore[arg-type]
            control = ui.number(label=self._label_for_field(field), value=num_val, precision=0).classes('w-full')
            self._controls[field.name] = control
            return

        if field.value_type is ValueType.FLOAT:
            num_val: float | None
            if value is None or value == '':
                num_val = None
            else:
                num_val = float(value)  # type: ignore[arg-type]
            control = ui.number(label=self._label_for_field(field), value=num_val).classes('w-full')
            self._controls[field.name] = control
            return

        control = ui.input(
            label=self._label_for_field(field),
            value='' if value is None else str(value),
        ).classes('w-full')
        self._controls[field.name] = control
