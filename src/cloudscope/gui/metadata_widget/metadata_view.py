"""Metadata cards for selected ``AcqImage`` metadata sections."""

from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import ApplyMetadataIntent, FileSelectionChanged, MetadataChanged
from cloudscope.gui.metadata_widget.schema_card_widget import SchemaCardWidget


class MetadataView:
    """Wires ``SchemaCardWidget`` to file selection and apply intents."""

    _UNSET = object()

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._container: ui.column | None = None
        self._last_file_id: str | None | object = MetadataView._UNSET
        self._cards: dict[str, SchemaCardWidget] = {}
        self._current_file_id: str | None = None
        self._current_acq_image: AcqImage | None = None
        self._event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self._event_bus.subscribe(MetadataChanged, self._on_metadata_changed)

    def build(self, parent: ui.element | None = None) -> ui.column:
        """Build the view root."""
        if parent is not None:
            with parent:
                self._container = ui.column().classes('w-full gap-2')
                with self._container:
                    ui.label('No file selected').classes('opacity-70')
        else:
            self._container = ui.column().classes('w-full gap-2')
            with self._container:
                ui.label('No file selected').classes('opacity-70')
        return self._container

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        if self._last_file_id is not MetadataView._UNSET and event.file_id == self._last_file_id:
            return
        self._last_file_id = event.file_id
        if self._container is None:
            return
        self._container.clear()
        self._cards = {}
        self._current_file_id = event.file_id
        self._current_acq_image = event.acq_image
        if event.file_id is None:
            with self._container:
                ui.label('No file selected').classes('opacity-70')
            return
        acq_image = event.acq_image
        if acq_image is None:
            with self._container:
                ui.label('No metadata for demo selection').classes('opacity-70')
            return
        self._build_cards(acq_image)

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh changed card values after controller applied a patch."""
        if event.file_id != self._current_file_id or self._current_acq_image is None:
            return
        card = self._cards.get(event.metadata_section_id)
        if card is None:
            return
        section = self._current_acq_image.get_metadata_section(event.metadata_section_id)
        card.update_values(section.get_values())

    def _build_cards(self, acq_image: AcqImage) -> None:
        with self._container:
            for section in acq_image.get_metadata_sections():
                section_id = str(section.metadata_section_id)
                card = SchemaCardWidget(
                    title=section.display_section_title,
                    schema=section.get_schema(),
                    values=section.get_values(),
                    on_apply=self._make_on_apply(section_id),
                )
                card.build()
                self._cards[section_id] = card

    def _make_on_apply(self, metadata_section_id: str) -> Callable[[dict[str, object]], None]:
        def _on_apply(patch: dict[str, object]) -> None:
            if self._current_file_id is None:
                return
            self._event_bus.publish(
                ApplyMetadataIntent(
                    file_id=self._current_file_id,
                    metadata_section_id=metadata_section_id,
                    patch=dict(patch),
                )
            )

        return _on_apply
