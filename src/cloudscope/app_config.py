"""GUI application config persistence for CloudScope."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

APP_NAME = 'cloudscope'
FILE_NAME = 'app_config.json'
SCHEMA_VERSION = 1
MAX_RECENTS = 15
DEFAULT_WINDOW_RECT = (100, 100, 1200, 1000)  # x, y, w, h
DEFAULT_FOLDER_DEPTH = 4
DEFAULT_TEXT_SIZE = 'text-base'
DEFAULT_TABLE_FONT_SIZE_PX = 13
MIN_TABLE_FONT_SIZE_PX = 8
MAX_TABLE_FONT_SIZE_PX = 32


def _normalize_path(path: str | Path) -> str:
    """Normalize a path for storage and comparisons."""
    p = Path(path).expanduser()
    try:
        p = p.resolve(strict=False)
    except Exception:
        pass
    return str(p)


def normalize_stored_path(path: str | Path) -> str:
    """Normalize a path the same way as stored config values (for comparisons)."""
    return _normalize_path(path)


@dataclass
class AppConfigData:
    """JSON-serializable GUI config payload."""

    schema_version: int = SCHEMA_VERSION
    recent_files: list[str] = field(default_factory=list)
    recent_folders: list[str] = field(default_factory=list)
    last_path: str = ''
    window_rect: list[int] = field(default_factory=lambda: list(DEFAULT_WINDOW_RECT))
    text_size: str = DEFAULT_TEXT_SIZE
    folder_depth: int = DEFAULT_FOLDER_DEPTH
    table_font_size_px: int = DEFAULT_TABLE_FONT_SIZE_PX
    dark_mode: bool = False

    def to_json_dict(self) -> dict[str, object]:
        """Return payload as JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_json_dict(cls, payload: dict[str, object]) -> AppConfigData:
        """Build config data from JSON payload with tolerant parsing."""
        schema_version_raw = payload.get('schema_version', -1)
        try:
            schema_version = int(schema_version_raw)
        except Exception:
            logger.warning('Invalid schema_version in app config payload: %r', schema_version_raw)
            schema_version = -1

        recent_files_raw = payload.get('recent_files', [])
        if isinstance(recent_files_raw, list):
            recent_files = [str(item) for item in recent_files_raw if isinstance(item, str) and item.strip()]
        else:
            recent_files = []

        recent_folders_raw = payload.get('recent_folders', [])
        if isinstance(recent_folders_raw, list):
            recent_folders = [str(item) for item in recent_folders_raw if isinstance(item, str) and item.strip()]
        else:
            recent_folders = []

        last_path_raw = payload.get('last_path', '')
        last_path = str(last_path_raw).strip() if isinstance(last_path_raw, str) else ''

        rect_raw = payload.get('window_rect', list(DEFAULT_WINDOW_RECT))
        window_rect = list(DEFAULT_WINDOW_RECT)
        if isinstance(rect_raw, list) and len(rect_raw) == 4:
            try:
                window_rect = [int(rect_raw[0]), int(rect_raw[1]), int(rect_raw[2]), int(rect_raw[3])]
            except Exception:
                window_rect = list(DEFAULT_WINDOW_RECT)

        text_size_raw = payload.get('text_size', DEFAULT_TEXT_SIZE)
        text_size = (
            str(text_size_raw).strip()
            if isinstance(text_size_raw, str) and str(text_size_raw).strip()
            else DEFAULT_TEXT_SIZE
        )

        folder_depth_raw = payload.get('folder_depth', DEFAULT_FOLDER_DEPTH)
        try:
            folder_depth = int(folder_depth_raw)
        except Exception:
            folder_depth = DEFAULT_FOLDER_DEPTH

        table_font_raw = payload.get('table_font_size_px', DEFAULT_TABLE_FONT_SIZE_PX)
        try:
            table_font_size_px = int(table_font_raw)
        except Exception:
            table_font_size_px = DEFAULT_TABLE_FONT_SIZE_PX

        dark_raw = payload.get('dark_mode', False)
        if isinstance(dark_raw, bool):
            dark_mode = dark_raw
        else:
            dark_mode = str(dark_raw).lower() in {'1', 'true', 'yes'}

        return cls(
            schema_version=schema_version,
            recent_files=recent_files,
            recent_folders=recent_folders,
            last_path=last_path,
            window_rect=window_rect,
            text_size=text_size,
            folder_depth=folder_depth,
            table_font_size_px=table_font_size_px,
            dark_mode=dark_mode,
        )


class AppConfig:
    """Manager for loading and saving ``AppConfigData`` to disk."""

    def __init__(self, *, path: Path, data: AppConfigData | None = None) -> None:
        self.path = path
        self.data = data if data is not None else AppConfigData()

    @staticmethod
    def default_config_path(
        *,
        app_name: str = APP_NAME,
        file_name: str = FILE_NAME,
        app_author: str | None = None,
    ) -> Path:
        """Return OS-appropriate config file path and ensure parent exists."""
        config_dir = Path(user_config_dir(app_name, app_author))
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / file_name

    @classmethod
    def load(
        cls,
        *,
        config_path: Path | None = None,
        app_name: str = APP_NAME,
        file_name: str = FILE_NAME,
        app_author: str | None = None,
        schema_version: int = SCHEMA_VERSION,
        reset_on_version_mismatch: bool = True,
        create_if_missing: bool = False,
    ) -> AppConfig:
        """Load app config from disk with schema-version handling."""
        path = config_path or cls.default_config_path(app_name=app_name, file_name=file_name, app_author=app_author)
        default_data = AppConfigData(schema_version=schema_version)
        try:
            raw = path.read_text(encoding='utf-8')
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                logger.warning('App config at %s is not a JSON object; using defaults', path)
                return cls(path=path, data=default_data)

            loaded = AppConfigData.from_json_dict(parsed)
            if int(loaded.schema_version) != int(schema_version):
                if reset_on_version_mismatch:
                    logger.warning(
                        'App config schema mismatch at %s: loaded=%s expected=%s; using defaults',
                        path,
                        loaded.schema_version,
                        schema_version,
                    )
                    return cls(path=path, data=default_data)
                loaded.schema_version = int(schema_version)

            cfg = cls(path=path, data=loaded)
            cfg._normalize_loaded_data()
            return cfg
        except FileNotFoundError:
            logger.info('App config not found at %s; using defaults', path)
            cfg = cls(path=path, data=default_data)
            if create_if_missing:
                cfg.save()
            return cfg
        except Exception as exc:
            logger.warning('Failed to load app config from %s (%s); using defaults', path, exc)
            return cls(path=path, data=default_data)

    def save(self) -> None:
        """Persist current config data to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data.to_json_dict(), indent=2), encoding='utf-8')

    def normalize_and_persist(self) -> None:
        """Normalize in-memory fields (paths, rects, depth) then write config to disk."""
        self._normalize_loaded_data()
        self.save()

    def ensure_exists(self) -> None:
        """Create config file if it does not exist."""
        if not self.path.exists():
            self.save()

    def _normalize_loaded_data(self) -> None:
        """Normalize loaded values; keep recent paths even when missing on disk.

        Recent file/folder lists are **not** pruned for missing targets at load time
        so temporarily unavailable volumes or deleted-then-restored paths stay in
        history until the user opens a missing item (handled in the GUI) or clears
        recents. Entries are still deduplicated by normalized path and capped.
        """
        normalized_files: list[str] = []
        seen_files: set[str] = set()
        for file_path in self.data.recent_files:
            normalized_path = _normalize_path(file_path)
            if not normalized_path.strip():
                continue
            if normalized_path in seen_files:
                continue
            seen_files.add(normalized_path)
            normalized_files.append(normalized_path)
        self.data.recent_files = normalized_files[-MAX_RECENTS:]

        normalized_folders: list[str] = []
        seen_folders: set[str] = set()
        for folder_path in self.data.recent_folders:
            normalized_path = _normalize_path(folder_path)
            if not normalized_path.strip():
                continue
            if normalized_path in seen_folders:
                continue
            seen_folders.add(normalized_path)
            normalized_folders.append(normalized_path)
        self.data.recent_folders = normalized_folders[-MAX_RECENTS:]

        if self.data.last_path:
            normalized_last = _normalize_path(self.data.last_path)
            last_obj = Path(normalized_last)
            if not last_obj.exists():
                logger.warning('Pruned missing last_path: %s', normalized_last)
                self.data.last_path = ''
            else:
                self.data.last_path = normalized_last

        rect = self.data.window_rect
        if not isinstance(rect, list) or len(rect) != 4:
            self.data.window_rect = list(DEFAULT_WINDOW_RECT)
        else:
            try:
                self.data.window_rect = [int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])]
            except Exception:
                self.data.window_rect = list(DEFAULT_WINDOW_RECT)

        if self.data.folder_depth < 1:
            self.data.folder_depth = DEFAULT_FOLDER_DEPTH

        if self.data.table_font_size_px < MIN_TABLE_FONT_SIZE_PX:
            self.data.table_font_size_px = MIN_TABLE_FONT_SIZE_PX
        elif self.data.table_font_size_px > MAX_TABLE_FONT_SIZE_PX:
            self.data.table_font_size_px = MAX_TABLE_FONT_SIZE_PX

    def get_recent_files(self) -> list[str]:
        """Return recent file paths."""
        return list(self.data.recent_files)

    def get_recent_folders(self) -> list[str]:
        """Return recent folder paths."""
        return list(self.data.recent_folders)

    def push_recent_file(self, path: str | Path) -> None:
        """Append or move file path to end of recent files."""
        normalized = _normalize_path(path)
        self.data.recent_files = [item for item in self.data.recent_files if _normalize_path(item) != normalized]
        self.data.recent_files.append(normalized)
        if len(self.data.recent_files) > MAX_RECENTS:
            self.data.recent_files = self.data.recent_files[-MAX_RECENTS:]

    def push_recent_folder(self, path: str | Path) -> None:
        """Append or move folder path to end of recent folders."""
        normalized = _normalize_path(path)
        self.data.recent_folders = [item for item in self.data.recent_folders if _normalize_path(item) != normalized]
        self.data.recent_folders.append(normalized)
        if len(self.data.recent_folders) > MAX_RECENTS:
            self.data.recent_folders = self.data.recent_folders[-MAX_RECENTS:]

    def remove_recent_file(self, path: str | Path) -> None:
        """Remove one file path from recents if present."""
        normalized = _normalize_path(path)
        self.data.recent_files = [item for item in self.data.recent_files if _normalize_path(item) != normalized]

    def remove_recent_folder(self, path: str | Path) -> None:
        """Remove one folder path from recents if present."""
        normalized = _normalize_path(path)
        self.data.recent_folders = [item for item in self.data.recent_folders if _normalize_path(item) != normalized]

    def clear_recent_paths(self) -> None:
        """Clear recent files and folders."""
        self.data.recent_files = []
        self.data.recent_folders = []

    def get_last_path(self) -> str:
        """Return last path string, where empty means unset."""
        return self.data.last_path

    def set_last_path(self, path: str | Path | None) -> None:
        """Set last path; ``None`` or empty value clears it."""
        if path is None:
            self.data.last_path = ''
            return
        value = str(path).strip()
        self.data.last_path = _normalize_path(value) if value else ''

    def set_window_rect(self, x: int, y: int, w: int, h: int) -> None:
        """Set native window rect as ``[x, y, w, h]``."""
        self.data.window_rect = [int(x), int(y), int(w), int(h)]

    def get_window_rect(self) -> tuple[int, int, int, int]:
        """Get native window rect as ``(x, y, w, h)``."""
        rect = self.data.window_rect
        if not isinstance(rect, list) or len(rect) != 4:
            return DEFAULT_WINDOW_RECT
        try:
            return (int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))
        except Exception:
            return DEFAULT_WINDOW_RECT

    def get_attribute(self, key: str) -> object | None:
        """Get attribute value by key.

        Args:
            key: Attribute name (e.g., ``text_size``, ``folder_depth``).

        Returns:
            Attribute value

        Raises:
            AttributeError: If key doesn't exist
        """
        if not hasattr(self.data, key):
            raise AttributeError(f"AppConfig has no attribute '{key}'")
        return getattr(self.data, key)
