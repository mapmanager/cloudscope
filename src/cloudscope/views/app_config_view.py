"""NiceGUI view for editing persisted CloudScope app settings.

Mirrors the metadata card pattern (``SchemaCardWidget`` + Apply) but is
independent of acquisition metadata: it reads/writes :class:`AppConfig` only.
"""

from __future__ import annotations

from collections.abc import Mapping

from nicegui import ui

from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from cloudscope.app_config import AppConfig, DEFAULT_TABLE_FONT_SIZE_PX
from cloudscope.views.metadata_widget.schema_card_widget import SchemaCardWidget
# from nicewidgets.gui_defaults import setUpGuiDefaults

# Tailwind classes supported by :func:`nicewidgets.gui_defaults.setUpGuiDefaults`.
_TEXT_SIZE_CHOICES: tuple[str, ...] = ('text-xs', 'text-sm', 'text-base', 'text-lg')

APP_CONFIG_UI_SCHEMA = SchemaDefinition(
    schema_id='cloudscope_app_config',
    version=1,
    fields=(
        FieldSchema(
            name='text_size',
            display_name='Text size',
            value_type=ValueType.ENUM,
            description='Default Tailwind text size class for NiceGUI widgets.',
            default_value='text-base',
            choices=_TEXT_SIZE_CHOICES,
            editable=True,
            visible=True,
        ),
        FieldSchema(
            name='folder_depth',
            display_name='Folder load depth',
            value_type=ValueType.INT,
            description='Maximum directory depth when loading a folder (must be ≥ 1).',
            default_value=4,
            editable=True,
            visible=True,
        ),
        FieldSchema(
            name='table_font_size_px',
            display_name='Table font size (px)',
            value_type=ValueType.INT,
            description='Font size for file-list table cells and headers (clamped on save).',
            default_value=DEFAULT_TABLE_FONT_SIZE_PX,
            editable=True,
            visible=True,
        ),
        FieldSchema(
            name='dark_mode',
            display_name='Dark mode',
            value_type=ValueType.BOOL,
            description='Use dark UI theme (reload header toggle if you change this here).',
            default_value=False,
            editable=True,
            visible=True,
        ),
    ),
)


class AppConfigView:
    """Build a schema-driven card bound to :class:`AppConfig` in-memory data."""

    def __init__(self, *, app_config: AppConfig) -> None:
        """Create the view.

        Args:
            app_config: Shared app config instance (same as load/save and home page).
        """
        self._app_config = app_config

    def _values_for_card(self) -> dict[str, object]:
        """Map current ``AppConfigData`` fields used by :data:`APP_CONFIG_UI_SCHEMA`."""
        data = self._app_config.data
        return {
            'text_size': data.text_size,
            'folder_depth': data.folder_depth,
            'table_font_size_px': data.table_font_size_px,
            'dark_mode': data.dark_mode,
        }

    def _on_apply(self, patch: Mapping[str, object]) -> None:
        """Apply editable fields, normalize, persist, and refresh global text defaults."""
        if 'text_size' in patch:
            raw = patch['text_size']
            choice = str(raw) if raw in _TEXT_SIZE_CHOICES else str(_TEXT_SIZE_CHOICES[2])
            self._app_config.data.text_size = choice
        if 'folder_depth' in patch:
            raw_fd = patch['folder_depth']
            try:
                fd = int(raw_fd)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                fd = 4
            self._app_config.data.folder_depth = max(1, fd)
        if 'table_font_size_px' in patch:
            raw_tf = patch['table_font_size_px']
            try:
                self._app_config.data.table_font_size_px = int(raw_tf)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        if 'dark_mode' in patch:
            self._app_config.data.dark_mode = bool(patch['dark_mode'])

        self._app_config.normalize_and_persist()
        # setUpGuiDefaults(self._app_config.data.text_size)
        ui.notify('App settings saved', type='positive')

    def build(self, parent: ui.element | None = None) -> SchemaCardWidget:
        """Build the settings card (optionally inside ``parent``).

        Args:
            parent: Optional NiceGUI container to build inside.

        Returns:
            The constructed :class:`SchemaCardWidget` instance.
        """
        card = SchemaCardWidget(
            title='App settings',
            schema=APP_CONFIG_UI_SCHEMA,
            values=self._values_for_card(),
            on_apply=lambda p: self._on_apply(p),
        )
        card.build(parent=parent)
        return card
