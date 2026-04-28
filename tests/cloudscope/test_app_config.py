"""Tests for GUI app config persistence."""

from __future__ import annotations

import json

from cloudscope.gui.app_config import AppConfig, MAX_RECENTS, SCHEMA_VERSION


def test_load_missing_returns_defaults(tmp_path) -> None:
    cfg_path = tmp_path / 'app_config.json'
    cfg = AppConfig.load(config_path=cfg_path, create_if_missing=False)

    assert cfg.get_last_path() == ''
    assert cfg.get_recent_files() == []
    assert cfg.get_recent_folders() == []
    assert cfg.get_window_rect() == (100, 100, 1200, 1000)


def test_roundtrip_save_and_load(tmp_path) -> None:
    cfg_path = tmp_path / 'app_config.json'
    cfg = AppConfig.load(config_path=cfg_path, create_if_missing=False)
    file_path = tmp_path / 'a.tif'
    file_path.write_text('x', encoding='utf-8')
    folder_path = tmp_path / 'folder'
    folder_path.mkdir()

    cfg.push_recent_file(file_path)
    cfg.push_recent_folder(folder_path)
    cfg.set_last_path(file_path)
    cfg.set_window_rect(10, 20, 900, 700)
    cfg.save()

    loaded = AppConfig.load(config_path=cfg_path)
    assert loaded.get_recent_files()[-1].endswith('a.tif')
    assert loaded.get_recent_folders()[-1].endswith('folder')
    assert loaded.get_last_path().endswith('a.tif')
    assert loaded.get_window_rect() == (10, 20, 900, 700)


def test_schema_mismatch_resets_to_defaults(tmp_path) -> None:
    cfg_path = tmp_path / 'app_config.json'
    cfg_path.write_text(
        json.dumps(
            {
                'schema_version': SCHEMA_VERSION - 1,
                'recent_files': ['/tmp/demo.tif'],
                'recent_folders': ['/tmp'],
                'last_path': '/tmp/demo.tif',
                'window_rect': [1, 2, 3, 4],
            }
        ),
        encoding='utf-8',
    )

    cfg = AppConfig.load(config_path=cfg_path, schema_version=SCHEMA_VERSION, reset_on_version_mismatch=True)
    assert cfg.get_recent_files() == []
    assert cfg.get_recent_folders() == []
    assert cfg.get_last_path() == ''
    assert cfg.get_window_rect() == (100, 100, 1200, 1000)


def test_push_recent_moves_existing_to_end_and_enforces_max(tmp_path) -> None:
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    file_paths = []
    for idx in range(MAX_RECENTS + 2):
        path = tmp_path / f'f{idx}.tif'
        path.write_text('x', encoding='utf-8')
        file_paths.append(path)
        cfg.push_recent_file(path)
    assert len(cfg.get_recent_files()) == MAX_RECENTS
    assert cfg.get_recent_files()[-1].endswith(f'f{MAX_RECENTS + 1}.tif')

    cfg.push_recent_file(file_paths[2])
    assert cfg.get_recent_files()[-1].endswith('f2.tif')


def test_prunes_missing_paths_with_warning(tmp_path, caplog) -> None:
    cfg_path = tmp_path / 'app_config.json'
    existing_folder = tmp_path / 'existing'
    existing_folder.mkdir()
    existing_file = tmp_path / 'keep.tif'
    existing_file.write_text('x', encoding='utf-8')
    missing_file = tmp_path / 'missing.tif'
    missing_folder = tmp_path / 'missing-folder'
    cfg_path.write_text(
        json.dumps(
            {
                'schema_version': SCHEMA_VERSION,
                'recent_files': [str(existing_file), str(missing_file)],
                'recent_folders': [str(existing_folder), str(missing_folder)],
                'last_path': str(missing_file),
                'window_rect': [100, 100, 1200, 1000],
            }
        ),
        encoding='utf-8',
    )

    cfg = AppConfig.load(config_path=cfg_path)
    assert cfg.get_recent_files() == [str(existing_file.resolve())]
    assert cfg.get_recent_folders() == [str(existing_folder.resolve())]
    assert cfg.get_last_path() == ''
    assert 'Pruned missing recent file' in caplog.text
    assert 'Pruned missing recent folder' in caplog.text
    assert 'Pruned missing last_path' in caplog.text
