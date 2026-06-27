"""Headless tests for ExperimentMetadataView non-build behavior."""

from __future__ import annotations

from acqstore.acq_image.metadata import ExperimentMetadata
from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from cloudscope.event_bus import EventBus
from cloudscope.events.metadata import ApplyMetadataIntent, MetadataChanged
from cloudscope.state import PrimarySelection
from cloudscope.views.metadata_widget.experiment_metadata_view import ExperimentMetadataView
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


class _FakeAcqImage:
    """Stand-in for AcqImage exposing metadata sections."""

    def __init__(self, sections: list[_FakeSection]) -> None:
        self._sections = {section.metadata_section_id: section for section in sections}

    def get_metadata_section(self, section_id: str) -> _FakeSection:
        return self._sections[section_id]


def _new_view() -> ExperimentMetadataView:
    return ExperimentMetadataView(event_bus=EventBus(), initially_visible=False)


def test_experiment_metadata_view_has_expected_view_id_and_initial_state() -> None:
    """ExperimentMetadataView should expose its view id and start with no current file."""
    view = _new_view()

    assert view.view_id is ViewId.EXPERIMENT_METADATA
    assert view._current_file_id is None
    assert view._current_acq_image is None
    assert view._last_file_id is ExperimentMetadataView._UNSET


def test_on_metadata_changed_ignored_for_other_file() -> None:
    """Metadata events for other files should not refresh the editor."""
    view = _new_view()
    section = _FakeSection(section_id='experiment_metadata', title='Experiment', values={'a': '1'})
    view._current_file_id = 'this-file'
    view._current_acq_image = _FakeAcqImage([section])  # type: ignore[assignment]

    called = False

    def _sync(acq_image):
        nonlocal called
        called = True

    view._editor.set_selected_acq_image = _sync  # type: ignore[method-assign]

    view._on_metadata_changed(
        MetadataChanged(
            file_id='other-file',
            metadata_section_id='experiment_metadata',
            file_list_row={},
        )
    )

    assert called is False


def test_on_metadata_changed_ignores_header_section() -> None:
    """Header metadata events should not refresh the experiment editor."""
    view = _new_view()
    view._current_file_id = 'f'
    view._current_acq_image = _FakeAcqImage([])  # type: ignore[assignment]

    synced: list[object] = []
    view._editor.set_selected_acq_image = lambda image: synced.append(image)  # type: ignore[method-assign]

    view._on_metadata_changed(
        MetadataChanged(
            file_id='f',
            metadata_section_id='acq_image_header',
            file_list_row={},
        )
    )

    assert synced == []


def test_on_metadata_changed_refreshes_experiment_editor() -> None:
    """Experiment metadata events should re-sync the experiment editor."""
    view = _new_view()
    section = _FakeSection(
        section_id=ExperimentMetadata.metadata_section_id,
        title='Experiment',
        values={'species': 'mouse'},
    )
    view._current_file_id = 'f'
    acq_image = _FakeAcqImage([section])
    view._current_acq_image = acq_image  # type: ignore[assignment]

    synced: list[object] = []
    view._editor.set_selected_acq_image = (  # type: ignore[method-assign]
        lambda image: synced.append(image)
    )

    view._on_metadata_changed(
        MetadataChanged(
            file_id='f',
            metadata_section_id=ExperimentMetadata.metadata_section_id,
            file_list_row={},
        )
    )

    assert synced == [acq_image]


def test_field_commit_publishes_single_field_intent() -> None:
    """Per-field commits should publish one-key patches."""
    bus = EventBus()
    intents: list[ApplyMetadataIntent] = []
    bus.subscribe(ApplyMetadataIntent, intents.append)

    view = ExperimentMetadataView(event_bus=bus, initially_visible=False)
    view._current_file_id = 'file-1'
    view._on_field_commit('species', 'mouse')

    assert len(intents) == 1
    assert intents[0].metadata_section_id == ExperimentMetadata.metadata_section_id
    assert intents[0].patch == {'species': 'mouse'}


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


def test_refresh_from_state_forces_redraw() -> None:
    """refresh_from_state should call _sync_selection with force=True."""
    view = _new_view()
    captured: dict[str, object] = {}

    def _capture(*, file_id, acq_image, force):
        captured.update(file_id=file_id, acq_image=acq_image, force=force)

    view._sync_selection = _capture  # type: ignore[method-assign]
    view.current_selection = PrimarySelection(file_id='f', channel=0, roi_id=1)
    view.current_acq_image = _FakeAcqImage([])  # type: ignore[assignment]

    view.refresh_from_state()

    assert captured['force'] is True
