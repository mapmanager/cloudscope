"""NiceGUI view for editing persisted CloudScope app settings.

Mirrors the metadata card pattern (``SchemaCardWidget`` + Apply) but is
independent of acquisition metadata: it reads/writes :class:`AppConfig` only.
"""

from __future__ import annotations

from collections.abc import Mapping

from nicegui import ui

from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from cloudscope.app_config import AppConfig, DEFAULT_TABLE_FONT_SIZE_PX
from cloudscope.event_bus import EventBus
from cloudscope.events import ResetHomeLayoutIntent
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
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


class AppConfigView(BaseView):
    """Build a schema-driven card bound to :class:`AppConfig` data.

    Args:
        app_config: Shared app config instance.
        event_bus: Page-scoped event bus.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.APP_CONFIG

    def __init__(
        self,
        *,
        app_config: AppConfig,
        event_bus: EventBus,
        initially_visible: bool = False,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._app_config = app_config
        self._card: SchemaCardWidget | None = None

    def _values_for_card(self) -> dict[str, object]:
        """Map current ``AppConfigData`` fields used by :data:`APP_CONFIG_UI_SCHEMA`.

        Returns:
            Values keyed by app-config schema field name.
        """
        data = self._app_config.data
        return {
            'text_size': data.text_size,
            'folder_depth': data.folder_depth,
            'table_font_size_px': data.table_font_size_px,
            'dark_mode': data.dark_mode,
        }

    def _on_apply(self, patch: Mapping[str, object]) -> None:
        """Apply editable fields, normalize, and persist app config.

        Args:
            patch: Partial app-config values from the schema card.

        Returns:
            None.
        """
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
        ui.notify('App settings saved', type='positive')


    def _on_reset_view_clicked(self) -> None:
        """Emit a request to reset Home page splitter layout.

        Returns:
            None.
        """
        self.event_bus.publish(ResetHomeLayoutIntent())

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the settings card.

        Args:
            parent: Optional NiceGUI parent to build inside.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.column().classes('w-full') as self.root:
                self._build_card()
        else:
            with parent:
                with ui.column().classes('w-full') as self.root:
                    self._build_card()
        self.after_build()
        return self.root

    def refresh_from_state(self) -> None:
        """Refresh card values from current app config.

        Returns:
            None.
        """
        if self._card is not None:
            self._card.update_values(self._values_for_card())

    def _build_card(self) -> None:
        """Build the schema card inside the current NiceGUI slot.

        Returns:
            None.
        """
        self._card = SchemaCardWidget(
            title='App settings',
            schema=APP_CONFIG_UI_SCHEMA,
            values=self._values_for_card(),
            on_apply=lambda p: self._on_apply(p),
        )
        self._card.build()
        ui.separator()
        ui.button('Reset View', on_click=self._on_reset_view_clicked).props('outline color=primary')
