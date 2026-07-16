"""Headless tests for ImageHeaderMetadataView non-build behavior."""

from __future__ import annotations

from acqstore.acq_image.metadata import (
    ExperimentMetadata,
    ImageHeaderMetadata,
    ReferenceImageMetadata,
)
from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from cloudscope.event_bus import EventBus
from cloudscope.events.metadata import ApplyMetadataIntent, MetadataChanged
from cloudscope.state import PrimarySelection
from cloudscope.views.metadata_widget.image_header_metadata_view import ImageHeaderMetadataView
from cloudscope.views.view_ids import ViewId


def _schema() -> SchemaDefinition:
    return SchemaDefinition(
        schema_id='s',
        version=1,
        fields=(FieldSchema(name='a', display_name='A', value_type=ValueType.STR),),
    )


class _FakeSection:
    """Stand-in for an acquisition image metadata section."""

    def __init__(
        self,
        *,
        section_id: str,
        title: str,
        values: dict[str, object],
    ) -> None:
        self.metadata_section_id = section_id
        self.display_section_title = title
        self._values = dict(values)

    def get_schema(self) -> SchemaDefinition:
        return _schema()

    def get_values(self) -> dict[str, object]:
        return dict(self._values)


class _FakeImages:
    """Stand-in for the file loader on ``AcqImage.images``."""

    def __init__(self, *, has_reference_image: bool = False) -> None:
        self.has_reference_image = has_reference_image


class _FakeAcqImage:
    """Stand-in for AcqImage exposing metadata sections."""

    def __init__(
        self,
        sections: list[_FakeSection],
        *,
        has_reference_image: bool = False,
    ) -> None:
        self._sections = {section.metadata_section_id: section for section in sections}
        self.images = _FakeImages(has_reference_image=has_reference_image)

    def get_metadata_section(self, section_id: str) -> _FakeSection:
        return self._sections[section_id]


class _FakeUiElement:
    """Minimal stand-in for a NiceGUI element with a ``visible`` flag."""

    def __init__(self) -> None:
        self.visible = False


def _new_view() -> ImageHeaderMetadataView:
    return ImageHeaderMetadataView(event_bus=EventBus(), initially_visible=False)


def test_image_header_metadata_view_has_expected_view_id_and_initial_state() -> None:
    """ImageHeaderMetadataView should expose its view id and start with no current file."""
    view = _new_view()

    assert view.view_id is ViewId.IMAGE_HEADER_METADATA
    assert view._current_file_id is None
    assert view._current_acq_image is None
    assert view._last_file_id is ImageHeaderMetadataView._UNSET


def test_on_metadata_changed_ignored_for_other_file() -> None:
    """Metadata events for other files should not refresh the header card."""
    view = _new_view()
    header = _FakeSection(
        section_id=ImageHeaderMetadata.metadata_section_id,
        title='Header',
        values={'physical_unit_x': 1.0},
    )
    view._current_file_id = 'this-file'
    view._current_acq_image = _FakeAcqImage([header])  # type: ignore[assignment]

    captured: list[dict[str, object]] = []
    view._header_card.update_values = lambda values: captured.append(dict(values))  # type: ignore[method-assign]

    view._on_metadata_changed(
        MetadataChanged(
            file_id='other-file',
            metadata_section_id=ImageHeaderMetadata.metadata_section_id,
            file_list_row={},
        )
    )

    assert captured == []


def test_on_metadata_changed_ignores_experiment_section() -> None:
    """Experiment metadata events should not refresh the header card."""
    view = _new_view()
    view._current_file_id = 'f'
    view._current_acq_image = _FakeAcqImage([])  # type: ignore[assignment]

    captured: list[dict[str, object]] = []
    view._header_card.update_values = lambda values: captured.append(dict(values))  # type: ignore[method-assign]

    view._on_metadata_changed(
        MetadataChanged(
            file_id='f',
            metadata_section_id=ExperimentMetadata.metadata_section_id,
            file_list_row={},
        )
    )

    assert captured == []


def test_on_metadata_changed_updates_header_card() -> None:
    """Image header metadata events should refresh the header card values."""
    view = _new_view()
    header = _FakeSection(
        section_id=ImageHeaderMetadata.metadata_section_id,
        title='Header',
        values={'physical_unit_x': 2.0},
    )
    view._current_file_id = 'f'
    view._current_acq_image = _FakeAcqImage([header])  # type: ignore[assignment]

    captured: list[dict[str, object]] = []
    view._header_card.update_values = lambda values: captured.append(dict(values))  # type: ignore[method-assign]

    view._on_metadata_changed(
        MetadataChanged(
            file_id='f',
            metadata_section_id=ImageHeaderMetadata.metadata_section_id,
            file_list_row={},
        )
    )

    assert captured == [{'physical_unit_x': 2.0}]


def test_header_apply_publishes_apply_metadata_intent() -> None:
    """The header Apply callback should publish an ApplyMetadataIntent."""
    bus = EventBus()
    intents: list[ApplyMetadataIntent] = []
    bus.subscribe(ApplyMetadataIntent, intents.append)

    view = ImageHeaderMetadataView(event_bus=bus, initially_visible=False)
    view._current_file_id = 'file-1'
    view._on_header_apply({'physical_unit_x': 2.0})

    assert len(intents) == 1
    assert intents[0].file_id == 'file-1'
    assert intents[0].metadata_section_id == ImageHeaderMetadata.metadata_section_id
    assert intents[0].patch == {'physical_unit_x': 2.0}


def test_sync_selection_skips_when_unchanged_and_not_forced() -> None:
    """Re-syncing the same file without force=True should be a no-op."""
    view = _new_view()
    view._last_file_id = 'f'
    view._current_file_id = 'f'

    view._sync_selection(file_id='f', acq_image=None, force=False)

    assert view._current_file_id == 'f'


def test_on_primary_selection_changed_delegates_to_sync_selection() -> None:
    """The lifecycle hook should call _sync_selection with force=False."""
    view = _new_view()
    captured: dict[str, object] = {}

    def _capture(*, file_id, acq_image, force):
        captured.update(file_id=file_id, acq_image=acq_image, force=force)

    view._sync_selection = _capture  # type: ignore[method-assign]
    view.current_selection = PrimarySelection(file_id='f', channel=0, roi_id=1)
    view.current_acq_image = _FakeAcqImage([])  # type: ignore[assignment]

    view.on_primary_selection_changed()

    assert captured['file_id'] == 'f'
    assert captured['force'] is False


def test_sync_selection_shows_no_reference_message_when_file_lacks_reference() -> None:
    """Files without a reference image should show the no-reference label."""
    view = _new_view()
    header = _FakeSection(
        section_id=ImageHeaderMetadata.metadata_section_id,
        title='Header',
        values={'physical_unit_x': 1.0},
    )
    acq = _FakeAcqImage([header], has_reference_image=False)
    view._no_reference_label = _FakeUiElement()
    view._reference_card_column = _FakeUiElement()

    view._sync_selection(file_id='f', acq_image=acq, force=True)  # type: ignore[arg-type]

    assert view._no_reference_label is not None
    assert view._no_reference_label.visible is True
    assert view._reference_card_column is not None
    assert view._reference_card_column.visible is False


def test_sync_selection_populates_reference_card_when_present() -> None:
    """Files with a reference image should populate the read-only reference card."""
    view = _new_view()
    header = _FakeSection(
        section_id=ImageHeaderMetadata.metadata_section_id,
        title='Header',
        values={'physical_unit_x': 1.0},
    )
    reference = _FakeSection(
        section_id=ReferenceImageMetadata.metadata_section_id,
        title='Reference Image',
        values={'physical_unit_x': 0.331, 'shape': '(512, 512)'},
    )
    acq = _FakeAcqImage([header, reference], has_reference_image=True)
    view._no_reference_label = _FakeUiElement()
    view._reference_card_column = _FakeUiElement()

    captured: list[dict[str, object]] = []
    view._reference_card.update_values = lambda values: captured.append(dict(values))  # type: ignore[method-assign]

    view._sync_selection(file_id='f', acq_image=acq, force=True)  # type: ignore[arg-type]

    assert view._no_reference_label is not None
    assert view._no_reference_label.visible is False
    assert view._reference_card_column is not None
    assert view._reference_card_column.visible is True
    assert captured == [{'physical_unit_x': 0.331, 'shape': '(512, 512)'}]
