"""Headless tests for SchemaCardWidget pure helpers and patch behavior."""

from __future__ import annotations

from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from cloudscope.views.metadata_widget.schema_card_widget import SchemaCardWidget


def _schema(fields: tuple[FieldSchema, ...]) -> SchemaDefinition:
    """Build a tiny SchemaDefinition for tests."""
    return SchemaDefinition(schema_id="test", version=1, fields=fields)


# ---- _label_for_field ----


def test_label_for_field_includes_unit_when_present() -> None:
    """A unit should be appended to the display name in parentheses."""
    card = SchemaCardWidget(
        title="t",
        schema=_schema(()),
        values={},
    )
    field = FieldSchema(name="x", display_name="X", value_type=ValueType.FLOAT, unit="um")

    assert card._label_for_field(field) == "X (um)"


def test_label_for_field_omits_unit_when_missing() -> None:
    """Display name alone is used when no unit is configured."""
    card = SchemaCardWidget(title="t", schema=_schema(()), values={})
    field = FieldSchema(name="x", display_name="X")

    assert card._label_for_field(field) == "X"


# ---- _stringify_readonly ----


def test_stringify_readonly_handles_none() -> None:
    """None should become an empty string for read-only display."""
    card = SchemaCardWidget(title="t", schema=_schema(()), values={})
    assert card._stringify_readonly(None) == ""


def test_stringify_readonly_handles_values() -> None:
    """Any non-None value should be str()'d for read-only display."""
    card = SchemaCardWidget(title="t", schema=_schema(()), values={})
    assert card._stringify_readonly(42) == "42"
    assert card._stringify_readonly(3.14) == "3.14"
    assert card._stringify_readonly("hello") == "hello"


# ---- _has_editable_fields ----


def test_has_editable_fields_false_when_all_readonly() -> None:
    """All-readonly schema should report no editable fields."""
    schema = _schema(
        (
            FieldSchema(name="a", display_name="A", visible=True, editable=False),
            FieldSchema(name="b", display_name="B", visible=False, editable=True),
        )
    )
    card = SchemaCardWidget(title="t", schema=schema, values={})
    assert card._has_editable_fields() is False


def test_has_editable_fields_true_when_one_visible_editable() -> None:
    """At least one visible+editable field should report True."""
    schema = _schema(
        (
            FieldSchema(name="a", display_name="A", visible=True, editable=True),
        )
    )
    card = SchemaCardWidget(title="t", schema=schema, values={})
    assert card._has_editable_fields() is True


# ---- _group_visible_fields ----


def test_group_visible_fields_preserves_first_appearance_order() -> None:
    """Groups should appear in the order their first field is encountered."""
    fields = (
        FieldSchema(name="a", display_name="A", visible=True, group="GroupB"),
        FieldSchema(name="b", display_name="B", visible=True, group="GroupA"),
        FieldSchema(name="c", display_name="C", visible=True, group="GroupB"),
        FieldSchema(name="d", display_name="D", visible=False, group="GroupZ"),
        FieldSchema(name="e", display_name="E", visible=True, group=None),
    )
    card = SchemaCardWidget(title="t", schema=_schema(fields), values={})

    groups = card._group_visible_fields()
    group_names = [name for name, _ in groups]

    assert group_names == ["GroupB", "GroupA", None]
    group_b_fields = [f.name for name, items in groups if name == "GroupB" for f in items]
    assert group_b_fields == ["a", "c"]


def test_group_visible_fields_skips_invisible_fields() -> None:
    """Invisible fields should not appear in any group."""
    fields = (
        FieldSchema(name="a", display_name="A", visible=False, group="x"),
        FieldSchema(name="b", display_name="B", visible=True, group="x"),
    )
    card = SchemaCardWidget(title="t", schema=_schema(fields), values={})

    groups = card._group_visible_fields()

    assert len(groups) == 1
    name, items = groups[0]
    assert name == "x"
    assert [f.name for f in items] == ["b"]


# ---- get_patch ----


class _FakeControl:
    """Fake NiceGUI control exposing a ``value`` attribute."""

    def __init__(self, value: object) -> None:
        self.value = value


def test_get_patch_returns_only_visible_editable_fields() -> None:
    """``get_patch`` should skip invisible/non-editable fields and missing controls."""
    schema = _schema(
        (
            FieldSchema(name="visible_edit", display_name="V", visible=True, editable=True),
            FieldSchema(name="readonly_field", display_name="R", visible=True, editable=False),
            FieldSchema(name="invisible_field", display_name="I", visible=False, editable=True),
            FieldSchema(name="no_control", display_name="X", visible=True, editable=True),
        )
    )
    card = SchemaCardWidget(title="t", schema=schema, values={})
    card._controls["visible_edit"] = _FakeControl("hello")
    card._controls["readonly_field"] = _FakeControl("read")
    card._controls["invisible_field"] = _FakeControl("hidden")

    patch = card.get_patch()

    assert patch == {"visible_edit": "hello"}


# ---- _apply triggers on_apply ----


def test_apply_invokes_on_apply_with_patch() -> None:
    """Internal ``_apply`` should pass the current ``get_patch()`` to ``on_apply``."""
    captured: dict[str, object] = {}
    schema = _schema(
        (
            FieldSchema(name="x", display_name="X", visible=True, editable=True),
        )
    )
    card = SchemaCardWidget(
        title="t",
        schema=schema,
        values={},
        on_apply=lambda patch: captured.update(patch=patch),
    )
    card._controls["x"] = _FakeControl(7)

    card._apply()

    assert captured == {"patch": {"x": 7}}


def test_apply_noop_when_no_callback() -> None:
    """``_apply`` should not raise when no ``on_apply`` callback is configured."""
    card = SchemaCardWidget(title="t", schema=_schema(()), values={})
    card._apply()


# ---- update_values ----


def test_update_values_updates_existing_controls_only() -> None:
    """``update_values`` should mutate matching controls and ignore the rest."""
    schema = _schema(
        (
            FieldSchema(name="x", display_name="X", visible=True, editable=True),
            FieldSchema(name="y", display_name="Y", visible=True, editable=True),
        )
    )
    card = SchemaCardWidget(title="t", schema=schema, values={"x": 1, "y": 2})

    class _RecordControl:
        def __init__(self, value: object) -> None:
            self.value = value
            self.updates = 0

        def update(self) -> None:
            self.updates += 1

    card._controls["x"] = _RecordControl(1)
    card._controls["y"] = _RecordControl(2)

    card.update_values({"x": 9, "z": 100})

    assert card._controls["x"].value == 9
    assert card._controls["x"].updates == 1
    assert card._controls["y"].value == 2
    assert card._controls["y"].updates == 0
