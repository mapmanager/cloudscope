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
class HomePageChromeState:
    """Page-composer chrome captured on client disconnect.

    Args:
        file_list_open: Whether the home file-list peek panel is open.
        analysis_plot_open: Whether the acq analysis plot panel is visible.
        reference_image_open: Whether the reference image panel is visible.
        velocity_pool_open: Whether the embedded velocity pool panel is visible.
    """

    file_list_open: bool
    analysis_plot_open: bool
    reference_image_open: bool
    velocity_pool_open: bool

    @classmethod
    def defaults(cls) -> HomePageChromeState:
        """Return the default home-page chrome used on first connect.

        Returns:
            Default chrome state matching ``HomePage.build`` defaults.
        """
        return cls(
            file_list_open=False,
            analysis_plot_open=True,
            reference_image_open=False,
            velocity_pool_open=True,
        )

    @classmethod
    def from_panel_open(cls, panel_open_state: dict[str, bool]) -> HomePageChromeState:
        """Build chrome state from the page ``panel_open_state`` mapping.

        Args:
            panel_open_state: Mutable page-local panel open flags.

        Returns:
            Captured chrome snapshot.
        """
        return cls(
            file_list_open=bool(panel_open_state['file_list']),
            analysis_plot_open=bool(panel_open_state['analysis_plot']),
            reference_image_open=bool(panel_open_state['reference_image']),
            velocity_pool_open=bool(panel_open_state['velocity_pool']),
        )


@dataclass(slots=True)
class HomePageSessionSnapshot:
    """Reconnect session snapshot stored on runtime between disconnect and rebuild.

    Args:
        chrome: Page-composer panel chrome.
        views: Per-view session blobs keyed by ``ViewId`` string values.
    """

    chrome: HomePageChromeState
    views: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> HomePageSessionSnapshot:
        """Return an empty snapshot for reconnect when none was captured.

        Returns:
            Snapshot with default chrome and no view blobs.
        """
        return cls(chrome=HomePageChromeState.defaults(), views={})
