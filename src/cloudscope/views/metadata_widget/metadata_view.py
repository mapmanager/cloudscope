"""Metadata cards for selected ``AcqImage`` metadata sections."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from cloudscope.event_bus import EventBus
from cloudscope.events import ApplyMetadataIntent, MetadataChanged
from cloudscope.views.base_view import BaseView
from cloudscope.views.metadata_widget.schema_card_widget import SchemaCardWidget
from cloudscope.views.view_ids import ViewId

from cloudscope.utils.logging import get_logger
logger = get_logger(__name__)


class MetadataView(BaseView):
    """Wires ``SchemaCardWidget`` to file selection and apply intents.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional home-page state used to refresh when the view
            becomes visible.
        initially_visible: Whether the view starts visible.
    """

    view_id = ViewId.METADATA
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
        self._last_file_id: str | None | object = MetadataView._UNSET
        self._cards: dict[str, SchemaCardWidget] = {}
        self._current_file_id: str | None = None
        self._current_acq_image: AcqImage | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the view root.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.column().classes("w-full gap-2") as self.root:
                self._container = ui.column().classes("w-full gap-2")
        else:
            with parent:
                with ui.column().classes("w-full gap-2") as self.root:
                    self._container = ui.column().classes("w-full gap-2")
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to metadata-related state events while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(MetadataChanged, self._on_metadata_changed))

    def refresh_from_state(self) -> None:
        """Refresh metadata cards from cached BaseView selection state.

        Returns:
            None.
        """
        self._render_file(
            file_id=self.current_selection.file_id,
            acq_image=self.current_acq_image,
            force=True,
        )

    def on_primary_selection_changed(self) -> None:
        """Refresh metadata cards after the primary selection changes.

        Returns:
            None.
        """
        self._render_file(
            file_id=self.current_selection.file_id,
            acq_image=self.current_acq_image,
            force=False,
        )

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh changed card values after controller applied a patch.

        Args:
            event: Metadata changed state event.

        Returns:
            None.
        """
        if event.file_id != self._current_file_id or self._current_acq_image is None:
            return
        card = self._cards.get(event.metadata_section_id)
        if card is None:
            return
        section = self._current_acq_image.get_metadata_section(event.metadata_section_id)
        card.update_values(section.get_values())

    def _render_file(
        self,
        *,
        file_id: str | None,
        acq_image: AcqImage | None,
        force: bool,
    ) -> None:
        """Render metadata cards for a selected file.

        Args:
            file_id: Selected file id.
            acq_image: Selected acquisition image, if available.
            force: Whether to redraw even if the file id did not change.

        Returns:
            None.
        """
        if not force and self._last_file_id is not MetadataView._UNSET and file_id == self._last_file_id:
            return
        self._last_file_id = file_id
        if self._container is None:
            return
        self._container.clear()
        self._cards = {}
        self._current_file_id = file_id
        self._current_acq_image = acq_image

        if file_id is None:
            self._render_no_file()
            return
        if acq_image is None:
            with self._container:
                ui.label("No metadata for demo selection").classes("opacity-70")
            return
        self._build_cards(acq_image)

    def _render_no_file(self) -> None:
        """Render no-file placeholder.

        Returns:
            None.
        """
        if self._container is None:
            return
        self._container.clear()
        self._cards = {}
        self._current_file_id = None
        self._current_acq_image = None
        with self._container:
            ui.label("No file selected").classes("opacity-70")

    def _build_cards(self, acq_image: AcqImage) -> None:
        """Build metadata cards for one acquisition image.

        Args:
            acq_image: Acquisition image whose metadata sections should render.

        Returns:
            None.
        """
        if self._container is None:
            return
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
        """Return callback that publishes an apply-metadata intent.

        Args:
            metadata_section_id: Backend metadata section identifier.

        Returns:
            Callback accepting a metadata patch.
        """
        def _on_apply(patch: dict[str, object]) -> None:
            if self._current_file_id is None:
                return
            self.event_bus.publish(
                ApplyMetadataIntent(
                    file_id=self._current_file_id,
                    metadata_section_id=metadata_section_id,
                    patch=dict(patch),
                )
            )

        return _on_apply
