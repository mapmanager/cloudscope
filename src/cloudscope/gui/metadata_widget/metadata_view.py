"""Metadata card for the selected ``AcqImage`` experiment section."""

from __future__ import annotations

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.acq_image_list import AcqImageList
from acqstore.acq_image.metadata import ExperimentMetadata
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import ApplyMetadataIntent, PrimarySelectionChanged
from cloudscope.gui.metadata_widget.schema_card_widget import SchemaCardWidget


class MetadataView:
    """Wires ``SchemaCardWidget`` to primary file selection and apply intents."""

    _UNSET = object()

    def __init__(self, event_bus: EventBus, acq_image_list: AcqImageList) -> None:
        self._event_bus = event_bus
        self._acq_image_list = acq_image_list
        self._container: ui.column | None = None
        self._last_file_id: str | None | object = MetadataView._UNSET
        self._card: SchemaCardWidget | None = None
        self._current_file_id: str | None = None
        self._event_bus.subscribe(PrimarySelectionChanged, self._on_selection_changed)

    def build(self, parent: ui.element | None = None) -> ui.column:
        """Build the view root."""
        if parent is not None:
            with parent:
                self._container = ui.column().classes('w-full gap-2')
                with self._container:
                    ui.label('No file selected').classes('text-sm opacity-70')
        else:
            self._container = ui.column().classes('w-full gap-2')
            with self._container:
                ui.label('No file selected').classes('text-sm opacity-70')
        return self._container

    def set_data(self, acq_image_list: AcqImageList) -> None:
        """Replace the backend file list reference."""
        self._acq_image_list = acq_image_list

    def _on_selection_changed(self, event: PrimarySelectionChanged) -> None:
        if self._last_file_id is not MetadataView._UNSET and event.file_id == self._last_file_id:
            return
        self._last_file_id = event.file_id
        if self._container is None:
            return
        self._container.clear()
        self._card = None
        self._current_file_id = event.file_id
        if event.file_id is None:
            with self._container:
                ui.label('No file selected').classes('text-sm opacity-70')
            return
        acq_image = self._acq_image_list.get_file_by_id(event.file_id)
        if acq_image is None:
            with self._container:
                ui.label('Selected file not found').classes('text-sm text-negative')
            return
        self._build_card(acq_image)

    def _build_card(self, acq_image: AcqImage) -> None:
        meta = acq_image.experimental_metadata
        with self._container:
            self._card = SchemaCardWidget(
                title=meta.display_section_title,
                schema=meta.get_schema(),
                values=meta.get_values(),
                on_apply=self._on_apply,
            )
            self._card.build()

    def _on_apply(self, patch: dict[str, object]) -> None:
        if self._current_file_id is None:
            return
        self._event_bus.publish(
            ApplyMetadataIntent(
                file_id=self._current_file_id,
                section_id=ExperimentMetadata.section_id,
                patch=dict(patch),
            )
        )
        if self._card is not None:
            acq = self._acq_image_list.get_file_by_id(self._current_file_id)
            if acq is not None:
                self._card.update_values(acq.experimental_metadata.get_values())
