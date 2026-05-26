"""Headless tests for MetadataView non-build behavior."""

from __future__ import annotations

from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from cloudscope.event_bus import EventBus
from cloudscope.events.metadata import ApplyMetadataIntent, MetadataChanged
from cloudscope.state import PrimarySelection
from cloudscope.views.metadata_widget.metadata_view import MetadataView
from cloudscope.views.metadata_widget.schema_card_widget import SchemaCardWidget
from cloudscope.views.view_ids import ViewId


def _schema() -> SchemaDefinition:
    return SchemaDefinition(
        schema_id="s",
        version=1,
        fields=(FieldSchema(name="a", display_name="A", value_type=ValueType.STR),),
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

    def set_values(self, values: dict[str, object]) -> None:
        self._values = dict(values)


class _FakeAcqImage:
    """Stand-in for AcqImage exposing metadata sections."""

    def __init__(self, sections: list[_FakeSection]) -> None:
        self._sections = {section.metadata_section_id: section for section in sections}

    def get_metadata_sections(self) -> list[_FakeSection]:
        return list(self._sections.values())

    def get_metadata_section(self, section_id: str) -> _FakeSection:
        return self._sections[section_id]


def _new_view() -> MetadataView:
    return MetadataView(event_bus=EventBus(), initially_visible=False)


# ---- view identity ----


def test_metadata_view_has_expected_view_id_and_initial_state() -> None:
    """MetadataView should expose its view id and start with no cards / no file."""
    view = _new_view()

    assert view.view_id is ViewId.METADATA
    assert view._cards == {}
    assert view._current_file_id is None
    assert view._current_acq_image is None
    assert view._last_file_id is MetadataView._UNSET


# ---- _on_metadata_changed ----


def test_on_metadata_changed_ignored_for_other_file() -> None:
    """Metadata events for other files should not update any card."""
    view = _new_view()
    section = _FakeSection(section_id="general", title="General", values={"a": "1"})
    view._current_file_id = "this-file"
    view._current_acq_image = _FakeAcqImage([section])

    card = SchemaCardWidget(title="t", schema=_schema(), values={"a": "0"})
    view._cards["general"] = card

    view._on_metadata_changed(
        MetadataChanged(
            file_id="other-file",
            metadata_section_id="general",
            file_list_row={},
        )
    )

    assert view._cards["general"] is card


def test_on_metadata_changed_ignored_when_section_not_present() -> None:
    """Unknown section ids should be silently ignored."""
    view = _new_view()
    section = _FakeSection(section_id="general", title="General", values={"a": "1"})
    view._current_file_id = "f"
    view._current_acq_image = _FakeAcqImage([section])

    view._on_metadata_changed(
        MetadataChanged(
            file_id="f",
            metadata_section_id="missing",
            file_list_row={},
        )
    )


def test_on_metadata_changed_updates_card_values() -> None:
    """Matching events should call update_values on the relevant card."""
    view = _new_view()
    section = _FakeSection(section_id="general", title="General", values={"a": "updated"})
    view._current_file_id = "f"
    view._current_acq_image = _FakeAcqImage([section])

    captured: list[dict[str, object]] = []

    class _Card:
        def update_values(self, values):
            captured.append(dict(values))

    view._cards["general"] = _Card()  # type: ignore[assignment]

    view._on_metadata_changed(
        MetadataChanged(
            file_id="f",
            metadata_section_id="general",
            file_list_row={},
        )
    )

    assert captured == [{"a": "updated"}]


# ---- _make_on_apply ----


def test_make_on_apply_publishes_apply_metadata_intent() -> None:
    """The on_apply callback should publish an ApplyMetadataIntent for the current file."""
    bus = EventBus()
    intents: list[ApplyMetadataIntent] = []
    bus.subscribe(ApplyMetadataIntent, intents.append)

    view = MetadataView(event_bus=bus, initially_visible=False)
    view._current_file_id = "file-1"
    on_apply = view._make_on_apply("general")

    on_apply({"x": 1, "y": "z"})

    assert len(intents) == 1
    assert intents[0].file_id == "file-1"
    assert intents[0].metadata_section_id == "general"
    assert intents[0].patch == {"x": 1, "y": "z"}


def test_make_on_apply_noop_when_no_current_file() -> None:
    """on_apply should be a no-op if no file is currently rendered."""
    bus = EventBus()
    intents: list[ApplyMetadataIntent] = []
    bus.subscribe(ApplyMetadataIntent, intents.append)
    view = MetadataView(event_bus=bus, initially_visible=False)

    view._make_on_apply("general")({"x": 1})

    assert intents == []


# ---- _render_file early returns ----


def test_render_file_skips_when_unchanged_and_not_forced() -> None:
    """Re-rendering the same file without force=True should be a no-op."""
    view = _new_view()
    view._last_file_id = "f"
    view._current_file_id = "f"

    view._render_file(file_id="f", acq_image=None, force=False)

    assert view._current_file_id == "f"


def test_render_file_noop_when_container_missing() -> None:
    """Without a built container, render should silently return."""
    view = _new_view()
    view._container = None

    view._render_file(file_id="new", acq_image=None, force=True)

    assert view._last_file_id == "new"


# ---- on_primary_selection_changed delegates ----


def test_on_primary_selection_changed_delegates_to_render_file() -> None:
    """The lifecycle hook should call _render_file with force=False."""
    view = _new_view()
    captured: dict[str, object] = {}

    def _capture(*, file_id, acq_image, force):
        captured.update(file_id=file_id, acq_image=acq_image, force=force)

    view._render_file = _capture  # type: ignore[method-assign]
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view.current_acq_image = _FakeAcqImage([])  # type: ignore[assignment]

    view.on_primary_selection_changed()

    assert captured["file_id"] == "f"
    assert captured["force"] is False


def test_refresh_from_state_forces_redraw() -> None:
    """refresh_from_state should call _render_file with force=True."""
    view = _new_view()
    captured: dict[str, object] = {}

    def _capture(*, file_id, acq_image, force):
        captured.update(file_id=file_id, acq_image=acq_image, force=force)

    view._render_file = _capture  # type: ignore[method-assign]
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view.current_acq_image = _FakeAcqImage([])  # type: ignore[assignment]

    view.refresh_from_state()

    assert captured["force"] is True
