"""Left-toolbar view for image-header metadata (read-only + calibration Apply)."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.metadata import IMAGE_HEADER_METADATA_SCHEMA, ImageHeaderMetadata
from cloudscope.event_bus import EventBus
from cloudscope.events.metadata import ApplyMetadataIntent, MetadataChanged
from cloudscope.views.base_view import BaseView
from cloudscope.views.metadata_widget.schema_card_widget import SchemaCardWidget
from cloudscope.views.view_ids import ViewId


class ImageHeaderMetadataView(BaseView):
    """Left-toolbar panel for ``AcqImage`` header metadata on the selected file.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional home-page state used to refresh when the view
            becomes visible.
        initially_visible: Whether the view starts visible.
    """

    view_id = ViewId.IMAGE_HEADER_METADATA
    _UNSET = object()

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        initially_visible: bool = False,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._container: ui.column | None = None
        self._card_column: ui.column | None = None
        self._no_file_label: ui.label | None = None
        self._demo_label: ui.label | None = None
        self._last_file_id: str | None | object = ImageHeaderMetadataView._UNSET
        self._header_card = SchemaCardWidget(
            title=ImageHeaderMetadata.display_section_title,
            schema=IMAGE_HEADER_METADATA_SCHEMA,
            values={},
            on_apply=self._on_header_apply,
            readonly_columns=2,
            editable_columns=2,
        )
        self._current_file_id: str | None = None
        self._current_acq_image: AcqImage | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the view root.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        root_classes = 'w-full gap-2 h-full min-h-0 flex-1 overflow-y-auto pr-1'

        def _build_inner() -> ui.column:
            with ui.column().classes(root_classes) as self.root:
                self._container = ui.column().classes('w-full gap-2')
                with self._container:
                    self._no_file_label = ui.label('No file selected').classes('opacity-70')
                    self._demo_label = ui.label('No metadata for demo selection').classes('opacity-70')
                    self._demo_label.visible = False
                    with ui.column().classes('w-full gap-2') as card_column:
                        self._card_column = card_column
                        self._header_card.build(parent=card_column)
                    self._card_column.visible = False
            return self.root

        if parent is None:
            _build_inner()
        else:
            with parent:
                _build_inner()

        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to image-header metadata state events while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(MetadataChanged, self._on_metadata_changed))

    def refresh_from_state(self) -> None:
        """Refresh the header card from cached BaseView selection state.

        Returns:
            None.
        """
        self._sync_selection(
            file_id=self.current_selection.file_id,
            acq_image=self.current_acq_image,
            force=True,
        )

    def on_primary_selection_changed(self) -> None:
        """Refresh the header card after the primary selection changes.

        Returns:
            None.
        """
        self._sync_selection(
            file_id=self.current_selection.file_id,
            acq_image=self.current_acq_image,
            force=False,
        )

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh header card values after controller applied a patch.

        Args:
            event: Metadata changed state event.

        Returns:
            None.
        """
        if event.metadata_section_id != ImageHeaderMetadata.metadata_section_id:
            return
        if event.file_id != self._current_file_id or self._current_acq_image is None:
            return
        section = self._current_acq_image.get_metadata_section(
            ImageHeaderMetadata.metadata_section_id
        )
        self._header_card.update_values(section.get_values())

    def _sync_selection(
        self,
        *,
        file_id: str | None,
        acq_image: AcqImage | None,
        force: bool,
    ) -> None:
        """Sync the header card for the selected file.

        Args:
            file_id: Selected file id.
            acq_image: Selected acquisition image, if available.
            force: Whether to redraw even if the file id did not change.
        """
        if not force and self._last_file_id is not ImageHeaderMetadataView._UNSET and file_id == self._last_file_id:
            return
        self._last_file_id = file_id
        self._current_file_id = file_id
        self._current_acq_image = acq_image

        if self._no_file_label is not None:
            self._no_file_label.visible = file_id is None
        if self._demo_label is not None:
            self._demo_label.visible = file_id is not None and acq_image is None
        if self._card_column is not None:
            self._card_column.visible = file_id is not None and acq_image is not None

        if file_id is None or acq_image is None:
            self._header_card.update_values({})
            return

        header_section = acq_image.get_metadata_section(ImageHeaderMetadata.metadata_section_id)
        self._header_card.update_values(header_section.get_values())

    def _on_header_apply(self, patch: dict[str, object]) -> None:
        """Publish an image-header metadata apply intent.

        Args:
            patch: Field patch from the header card Apply button.

        Returns:
            None.
        """
        if self._current_file_id is None:
            return
        self.event_bus.publish(
            ApplyMetadataIntent(
                file_id=self._current_file_id,
                metadata_section_id=ImageHeaderMetadata.metadata_section_id,
                patch=dict(patch),
            )
        )
