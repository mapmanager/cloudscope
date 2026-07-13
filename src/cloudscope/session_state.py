"""Reconnect session snapshot types and view blob validation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cloudscope.state import PrimarySelection
from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

VIEW_SESSION_SCHEMA_VERSION = 1


def require_keys(data: dict[str, Any], *keys: str) -> None:
    """Raise when any required key is absent from a session blob.

    Args:
        data: Session blob mapping.
        *keys: Required key names.

    Raises:
        KeyError: When one or more keys are missing.
    """
    missing = [key for key in keys if key not in data]
    if missing:
        raise KeyError(f'session blob missing keys: {missing}')


def require_schema_version(data: dict[str, Any], *, expected: int = VIEW_SESSION_SCHEMA_VERSION) -> None:
    """Validate the schema version field in a view session blob.

    Args:
        data: Session blob mapping.
        expected: Required schema version.

    Raises:
        KeyError: When ``schema_version`` is missing.
        ValueError: When the version does not match ``expected``.
    """
    require_keys(data, 'schema_version')
    version = data['schema_version']
    if version != expected:
        raise ValueError(f'unsupported session blob schema_version: {version!r}')


def selection_guard_from_selection(selection: PrimarySelection) -> dict[str, Any]:
    """Return a selection guard dict for export blobs.

    Args:
        selection: Current primary selection.

    Returns:
        Guard mapping with file/channel/roi/analysis fields.
    """
    return {
        'file_id': selection.file_id,
        'channel': selection.channel,
        'roi_id': selection.roi_id,
        'analysis_name': selection.analysis_name,
    }


def selection_guard_matches(data: dict[str, Any], selection: PrimarySelection) -> bool:
    """Return whether a blob guard matches the current primary selection.

    Args:
        data: Session blob containing ``selection_guard``.
        selection: Selection to compare against.

    Returns:
        True when the guard matches or is absent.
    """
    guard = data.get('selection_guard')
    if guard is None:
        return True
    return (
        guard.get('file_id') == selection.file_id
        and guard.get('channel') == selection.channel
        and guard.get('roi_id') == selection.roi_id
        and guard.get('analysis_name') == selection.analysis_name
    )


@dataclass(slots=True)
class HomePageRestorableState:
    """Serializable app-level home-page state (no live runtime objects).

    This is the typed, JSON-safe contract for "what CloudScope is showing"
    at the app level: primary selection, the shared x-range, and the file ids
    in display order. It intentionally excludes non-serializable runtime fields
    such as the backend ``AcqImageList`` and callables.

    It is a foundation for reconnect diagnostics, the debug view, and future
    shareable view-state URLs. As of this ticket it is captured on disconnect
    but not yet used to drive restore (restore still reads live controller
    state); see the reconnect roadmap.

    Args:
        selection: Current primary selection.
        primary_x_range: Shared ``(x_min, x_max)`` pair; ``(None, None)`` means
            auto.
        file_ids: Stable file identifiers in display order.
        schema_version: Session blob schema version.
    """

    selection: PrimarySelection
    primary_x_range: tuple[float | None, float | None] = (None, None)
    file_ids: tuple[str, ...] = ()
    schema_version: int = VIEW_SESSION_SCHEMA_VERSION

    @classmethod
    def empty(cls) -> HomePageRestorableState:
        """Return empty restorable state with no selection and auto x-range.

        Returns:
            Default restorable state.
        """
        return cls(selection=PrimarySelection())

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation.

        Returns:
            Mapping with schema version, selection, x-range, and file ids.
        """
        x_min, x_max = self.primary_x_range
        return {
            'schema_version': self.schema_version,
            'selection': selection_guard_from_selection(self.selection),
            'primary_x_range': [x_min, x_max],
            'file_ids': list(self.file_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HomePageRestorableState:
        """Build restorable state from a mapping produced by :meth:`to_dict`.

        Args:
            data: Mapping produced by :meth:`to_dict`.

        Returns:
            Reconstructed restorable state.

        Raises:
            KeyError: If required keys (including ``schema_version``) are absent.
            ValueError: If ``schema_version`` is unsupported.
        """
        require_schema_version(data)
        require_keys(data, 'selection', 'primary_x_range', 'file_ids')
        selection = data['selection']
        x_range = data['primary_x_range']
        return cls(
            selection=PrimarySelection(
                file_id=selection.get('file_id'),
                channel=selection.get('channel'),
                roi_id=selection.get('roi_id'),
                analysis_name=selection.get('analysis_name'),
            ),
            primary_x_range=(x_range[0], x_range[1]),
            file_ids=tuple(str(file_id) for file_id in data['file_ids']),
            schema_version=int(data.get('schema_version', VIEW_SESSION_SCHEMA_VERSION)),
        )


@dataclass(slots=True)
class HomePageChromeState:
    """Page-level layout chrome captured on client disconnect.

    These fields describe the state of the home page shell itself (panels the
    page composer owns), not the internal state of widgets hosted inside those
    panels. Splitter drag positions are intentionally excluded because
    ``SplitterManager`` already persists them in ``AppConfig``; only the
    open/closed toggles that ``AppConfig`` does not restore live here.

    Args:
        file_list_open: Whether the home file-list peek panel is open.
        analysis_plot_open: Whether the acq analysis plot panel is visible.
        left_toolbar_active_view_id: ``ViewId`` string of the active left
            toolbar tab, or ``None`` when the left toolbar panel is collapsed.
            The left toolbar is open exactly when this is not ``None``.
        right_pool_open: Whether the right-side analysis pool panel is expanded.
    """

    file_list_open: bool
    analysis_plot_open: bool
    left_toolbar_active_view_id: str | None
    right_pool_open: bool

    @classmethod
    def defaults(cls) -> HomePageChromeState:
        """Return the default home-page chrome used on first connect.

        Returns:
            Default chrome state matching ``HomePage.build`` defaults.
        """
        return cls(
            file_list_open=False,
            analysis_plot_open=True,
            left_toolbar_active_view_id=None,
            right_pool_open=False,
        )

    @classmethod
    def capture(
        cls,
        *,
        file_list_open: bool,
        analysis_plot_open: bool,
        left_toolbar_active_view_id: str | None,
        right_pool_open: bool,
    ) -> HomePageChromeState:
        """Build chrome state from live page-layout values at disconnect.

        Args:
            file_list_open: Current home file-list panel open flag.
            analysis_plot_open: Current acq analysis plot panel open flag.
            left_toolbar_active_view_id: Active left toolbar tab id string, or
                ``None`` when the left toolbar is collapsed.
            right_pool_open: Whether the right analysis pool panel is expanded.

        Returns:
            Captured chrome snapshot.
        """
        return cls(
            file_list_open=bool(file_list_open),
            analysis_plot_open=bool(analysis_plot_open),
            left_toolbar_active_view_id=(
                str(left_toolbar_active_view_id)
                if left_toolbar_active_view_id is not None
                else None
            ),
            right_pool_open=bool(right_pool_open),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of page chrome.

        Returns:
            Mapping with the page-level layout chrome fields.
        """
        return {
            'file_list_open': bool(self.file_list_open),
            'analysis_plot_open': bool(self.analysis_plot_open),
            'left_toolbar_active_view_id': self.left_toolbar_active_view_id,
            'right_pool_open': bool(self.right_pool_open),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HomePageChromeState:
        """Build chrome state from a mapping produced by :meth:`to_dict`.

        Args:
            data: Mapping produced by :meth:`to_dict`.

        Returns:
            Reconstructed chrome state.

        Raises:
            KeyError: If required keys are absent.
        """
        require_keys(
            data,
            'file_list_open',
            'analysis_plot_open',
            'left_toolbar_active_view_id',
            'right_pool_open',
        )
        active_view_id = data['left_toolbar_active_view_id']
        return cls(
            file_list_open=bool(data['file_list_open']),
            analysis_plot_open=bool(data['analysis_plot_open']),
            left_toolbar_active_view_id=(
                str(active_view_id) if active_view_id is not None else None
            ),
            right_pool_open=bool(data['right_pool_open']),
        )


@dataclass(slots=True)
class HomePageSessionSnapshot:
    """Reconnect session snapshot stored on runtime between disconnect and rebuild.

    Args:
        chrome: Page-composer panel chrome.
        app_state: App-level restorable state captured at disconnect. Captured
            for diagnostics/serialization; restore currently reads live
            controller state rather than this field.
        views: Per-view session blobs keyed by ``ViewId`` string values.
    """

    chrome: HomePageChromeState
    app_state: HomePageRestorableState = field(default_factory=HomePageRestorableState.empty)
    views: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> HomePageSessionSnapshot:
        """Return an empty snapshot for reconnect when none was captured.

        Returns:
            Snapshot with default chrome, empty app state, and no view blobs.
        """
        return cls(
            chrome=HomePageChromeState.defaults(),
            app_state=HomePageRestorableState.empty(),
            views={},
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the snapshot.

        Per-view blobs are copied structurally. They are serializable by
        convention (each view's ``export_session_state`` returns JSON-safe
        data); this method does not deep-validate nested view blobs.

        Returns:
            Mapping with schema version, app state, chrome, and view blobs.
        """
        return {
            'schema_version': VIEW_SESSION_SCHEMA_VERSION,
            'app_state': self.app_state.to_dict(),
            'chrome': self.chrome.to_dict(),
            'views': {view_id: dict(blob) for view_id, blob in self.views.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HomePageSessionSnapshot:
        """Build a snapshot from a mapping produced by :meth:`to_dict`.

        Args:
            data: Mapping produced by :meth:`to_dict`.

        Returns:
            Reconstructed snapshot.

        Raises:
            KeyError: If required keys (including ``schema_version``) are absent.
            ValueError: If ``schema_version`` is unsupported.
        """
        require_schema_version(data)
        require_keys(data, 'app_state', 'chrome', 'views')
        return cls(
            chrome=HomePageChromeState.from_dict(data['chrome']),
            app_state=HomePageRestorableState.from_dict(data['app_state']),
            views={
                str(view_id): dict(blob)
                for view_id, blob in dict(data['views']).items()
            },
        )
