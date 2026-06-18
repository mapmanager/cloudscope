"""Per-user runtime context for CloudScope page construction."""

from __future__ import annotations

import os
import re
import shutil
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from platformdirs import user_cache_dir, user_data_dir

from nicegui import app

from cloudscope.app_config import AppConfig
from cloudscope.quota import StorageQuota, mb_to_bytes
from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

APP_NAME = 'cloudscope'
DATA_DIR_ENV = 'CLOUDSCOPE_DATA_DIR'
DEMO_SESSION_QUOTA_MB_ENV = 'CLOUDSCOPE_DEMO_SESSION_QUOTA_MB'
DEMO_MAX_UPLOAD_MB_ENV = 'CLOUDSCOPE_DEMO_MAX_UPLOAD_MB'
DEMO_MAX_SESSION_AGE_HOURS_ENV = 'CLOUDSCOPE_DEMO_MAX_SESSION_AGE_HOURS'
DEFAULT_DEMO_SESSION_QUOTA_MB = 500
DEFAULT_DEMO_MAX_UPLOAD_MB = 250
DEFAULT_DEMO_MAX_SESSION_AGE_HOURS = 24
LAST_USED_FILE_NAME = '.last_used'

_SAFE_ID_RE = re.compile(r'[^a-zA-Z0-9_.-]+')


class UserContextKind(StrEnum):
    """Supported CloudScope user/workspace context kinds."""

    LOCAL_OS_USER = 'local_os_user'
    SERVER_DEMO = 'server_demo'
    SERVER_AUTH_USER = 'server_auth_user'


@dataclass(frozen=True, slots=True)
class UserContext:
    """Resolved per-page user/workspace context.

    Attributes:
        kind: User/workspace context kind.
        user_id: Stable identifier within the context kind.
        config_path: Path used for this user's ``AppConfig``.
        data_dir: Root data directory for this user/session.
        upload_dir: Directory used for browser-uploaded acquisition files.
        sample_data_dir: Directory used by sample-data loading.
        cache_dir: Cache/temp directory for this user/session.
        quota: Optional upload and total-storage limits.
        last_used_path: Optional marker touched for disposable demo cleanup.
        persistent: Whether config/uploads should persist across sessions.
    """

    kind: UserContextKind
    user_id: str
    config_path: Path
    data_dir: Path
    upload_dir: Path
    sample_data_dir: Path
    cache_dir: Path
    quota: StorageQuota = StorageQuota()
    last_used_path: Path | None = None
    persistent: bool = True

    @property
    def is_demo(self) -> bool:
        """Return whether this context is an anonymous demo session."""
        return self.kind is UserContextKind.SERVER_DEMO

    @property
    def quota_bytes(self) -> int | None:
        """Return the total workspace quota in bytes, if configured."""
        return self.quota.quota_bytes

    @property
    def max_upload_bytes(self) -> int | None:
        """Return the per-upload limit in bytes, if configured."""
        return self.quota.max_upload_bytes

    def load_app_config(self, *, create_if_missing: bool = False) -> AppConfig:
        """Load ``AppConfig`` for this context.

        Demo contexts intentionally start from defaults and do not read or save
        persisted config so the public demo remains controlled.
        """
        if self.is_demo:
            return AppConfig.ephemeral(config_path=self.config_path)
        return AppConfig.load(config_path=self.config_path, create_if_missing=create_if_missing)

    def touch_last_used(self) -> None:
        """Update the disposable-session marker when one is configured."""
        if self.last_used_path is None:
            return
        self.last_used_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_used_path.write_text(str(int(time.time())), encoding='utf-8')


_TRUE_VALUES = {'1', 'true', 'yes', 'y', 'on'}
_FALSE_VALUES = {'0', 'false', 'no', 'n', 'off'}


def get_or_create_demo_session_id() -> str | None:
    """Return a browser-stable demo session id when NiceGUI storage is available.

    Returns:
        Existing or newly created demo session id, or ``None`` when browser
        storage is unavailable.
    """
    try:
        browser_storage = app.storage.browser
    except Exception:
        logger.debug('NiceGUI browser storage unavailable for demo session id', exc_info=True)
        return None
    key = 'cloudscope_demo_session_id'
    value = browser_storage.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    value = uuid4().hex
    browser_storage[key] = value
    return value


def resolve_user_context_from_env(
    *,
    auth_user_id: str | None = None,
    demo_session_id: str | None = None,
) -> UserContext:
    """Resolve a user context from CloudScope runtime environment variables."""
    remote = _parse_bool_env('CLOUDSCOPE_REMOTE', default=False)
    native = _parse_bool_env('CLOUDSCOPE_NATIVE', default=not remote)
    return resolve_user_context(
        remote=remote,
        native=native,
        auth_user_id=auth_user_id,
        demo_session_id=demo_session_id,
    )


def _parse_bool_env(name: str, *, default: bool) -> bool:
    """Parse a CloudScope boolean environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    logger.warning('Invalid boolean for %s=%r; using %r', name, raw, default)
    return default


def _parse_positive_int_env(name: str, *, default: int) -> int:
    """Parse a positive integer environment variable with a default."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == '':
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning('Invalid integer for %s=%r; using %r', name, raw, default)
        return default
    if value <= 0:
        logger.warning('Non-positive integer for %s=%r; using %r', name, raw, default)
        return default
    return value


def safe_user_id(raw: str) -> str:
    """Return a filesystem-safe user id fragment."""
    cleaned = _SAFE_ID_RE.sub('_', raw.strip().lower()).strip('._-')
    return cleaned or 'user'


def get_server_data_root() -> Path:
    """Return the server data root used in remote deployments.

    Resolution order:
        1. ``CLOUDSCOPE_DATA_DIR`` when set.
        2. ``/data`` when it exists.
        3. platformdirs user data dir for local development fallback.
    """
    env_path = os.getenv(DATA_DIR_ENV)
    if env_path:
        return Path(env_path).expanduser().resolve(strict=False)
    data_mount = Path('/data')
    if data_mount.exists():
        return data_mount
    return Path(user_data_dir(APP_NAME))


def resolve_user_context(
    *,
    remote: bool,
    native: bool,
    user_id: str | None = None,
    auth_user_id: str | None = None,
    demo_session_id: str | None = None,
) -> UserContext:
    """Resolve the CloudScope user context for page construction."""
    if not remote or native:
        return _local_os_user_context(user_id=user_id)
    if auth_user_id:
        return _server_auth_user_context(auth_user_id)
    return _server_demo_context(session_id=demo_session_id)


def cleanup_expired_demo_sessions(
    *,
    demo_root: Path,
    max_age_seconds: int,
    now: float | None = None,
) -> int:
    """Delete expired disposable demo-session directories.

    A session expires when its ``.last_used`` marker, or directory mtime when
    the marker is absent, is older than ``max_age_seconds``.

    Returns:
        Number of session directories removed.
    """
    root = Path(demo_root)
    if not root.exists():
        return 0
    cutoff = (time.time() if now is None else float(now)) - int(max_age_seconds)
    removed = 0
    for session_dir in root.iterdir():
        if not session_dir.is_dir():
            continue
        marker = session_dir / LAST_USED_FILE_NAME
        try:
            last_used = marker.stat().st_mtime if marker.exists() else session_dir.stat().st_mtime
        except OSError:
            continue
        if last_used >= cutoff:
            continue
        try:
            shutil.rmtree(session_dir)
            removed += 1
        except OSError:
            logger.warning('Failed to remove expired demo session %s', session_dir, exc_info=True)
    return removed


def _local_os_user_context(*, user_id: str | None = None) -> UserContext:
    """Return a context for a desktop/local OS user."""
    data_dir = Path(user_data_dir(APP_NAME))
    cache_dir = Path(user_cache_dir(APP_NAME))
    return UserContext(
        kind=UserContextKind.LOCAL_OS_USER,
        user_id=safe_user_id(user_id or 'local'),
        config_path=AppConfig.default_config_path(),
        data_dir=data_dir,
        upload_dir=data_dir / 'uploads',
        sample_data_dir=data_dir / 'sample-data',
        cache_dir=cache_dir,
        persistent=True,
    )


def _server_auth_user_context(auth_user_id: str) -> UserContext:
    """Return a persistent server context for an authenticated user."""
    safe_id = safe_user_id(auth_user_id)
    root = get_server_data_root()
    user_dir = root / 'users' / safe_id
    return UserContext(
        kind=UserContextKind.SERVER_AUTH_USER,
        user_id=safe_id,
        config_path=user_dir / 'app_config.json',
        data_dir=user_dir,
        upload_dir=user_dir / 'uploads',
        sample_data_dir=user_dir / 'sample-data',
        cache_dir=user_dir / 'cache',
        persistent=True,
    )


def _server_demo_context(*, session_id: str | None = None) -> UserContext:
    """Return a non-persistent server demo context."""
    root = get_server_data_root()
    demo_root = _demo_sessions_root(root)
    max_age_hours = _parse_positive_int_env(
        DEMO_MAX_SESSION_AGE_HOURS_ENV,
        default=DEFAULT_DEMO_MAX_SESSION_AGE_HOURS,
    )
    cleanup_expired_demo_sessions(
        demo_root=demo_root,
        max_age_seconds=max_age_hours * 60 * 60,
    )

    demo_id = safe_user_id(session_id or uuid4().hex)
    demo_dir = demo_root / demo_id
    context = UserContext(
        kind=UserContextKind.SERVER_DEMO,
        user_id=demo_id,
        config_path=demo_dir / 'app_config.json',
        data_dir=demo_dir,
        upload_dir=demo_dir / 'uploads',
        sample_data_dir=root / 'shared' / 'sample-data',
        cache_dir=demo_dir / 'cache',
        quota=StorageQuota(
            quota_bytes=mb_to_bytes(
                _parse_positive_int_env(
                    DEMO_SESSION_QUOTA_MB_ENV,
                    default=DEFAULT_DEMO_SESSION_QUOTA_MB,
                )
            ),
            max_upload_bytes=mb_to_bytes(
                _parse_positive_int_env(
                    DEMO_MAX_UPLOAD_MB_ENV,
                    default=DEFAULT_DEMO_MAX_UPLOAD_MB,
                )
            ),
        ),
        last_used_path=demo_dir / LAST_USED_FILE_NAME,
        persistent=False,
    )
    context.touch_last_used()
    return context


def _demo_sessions_root(root: Path) -> Path:
    """Return the root directory for disposable demo sessions."""
    return root / 'tmp' / 'demo-sessions'
