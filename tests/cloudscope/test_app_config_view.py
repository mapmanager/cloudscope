"""Tests for app config UI schema alignment with ``AppConfigData``."""

from __future__ import annotations

from dataclasses import fields

from cloudscope.app_config import AppConfigData
from cloudscope.views.app_config_view import APP_CONFIG_UI_SCHEMA


def test_app_config_ui_schema_field_names_exist_on_dataclass() -> None:
    data_field_names = {f.name for f in fields(AppConfigData)}
    for field in APP_CONFIG_UI_SCHEMA.fields:
        assert field.name in data_field_names, f'schema field {field.name!r} missing on AppConfigData'


def test_app_config_ui_schema_editable_subset() -> None:
    editable = {f.name for f in APP_CONFIG_UI_SCHEMA.fields if f.editable}
    assert editable == {'text_size', 'folder_depth', 'table_font_size_px', 'dark_mode'}
