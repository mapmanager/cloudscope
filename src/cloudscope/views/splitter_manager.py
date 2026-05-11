"""Programmatic management for Home page NiceGUI splitters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cloudscope.app_config import (
    DEFAULT_HOME_ANALYSIS_REFERENCE_SPLITTER_PCT,
    DEFAULT_HOME_FILE_LIST_SPLITTER_PCT,
    DEFAULT_HOME_LEFT_TOOLBAR_OPEN_SPLITTER_PCT,
    DEFAULT_HOME_PRIMARY_IMAGE_SPLITTER_PCT,
    HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT,
    HOME_LEFT_TOOLBAR_COLLAPSED_SLACK_PCT,
    AppConfig,
)


class SplitterId(StrEnum):
    """Managed Home page splitter identifiers."""

    LEFT_TOOLBAR = 'left_toolbar'
    FILE_LIST = 'file_list'
    PRIMARY_IMAGE = 'primary_image'
    ANALYSIS_REFERENCE = 'analysis_reference'


@dataclass(frozen=True, slots=True)
class SplitterPreset:
    """Factory/default configuration for one splitter.

    Args:
        splitter_id: Managed splitter id.
        default_value: Default value as a percentage of the ``before`` pane.
        limits: Minimum and maximum allowed values.
    """

    splitter_id: SplitterId
    default_value: float
    limits: tuple[float, float]

    def clamp(self, value: float) -> float:
        """Clamp a splitter value to this preset's limits.

        Args:
            value: Raw splitter value.

        Returns:
            Clamped splitter value.
        """
        lower, upper = self.limits
        return max(lower, min(upper, float(value)))


HOME_SPLITTER_PRESETS: dict[SplitterId, SplitterPreset] = {
    SplitterId.LEFT_TOOLBAR: SplitterPreset(
        SplitterId.LEFT_TOOLBAR,
        HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT,
        (HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT, 70.0),
    ),
    SplitterId.FILE_LIST: SplitterPreset(SplitterId.FILE_LIST, DEFAULT_HOME_FILE_LIST_SPLITTER_PCT, (5.0, 60.0)),
    SplitterId.PRIMARY_IMAGE: SplitterPreset(SplitterId.PRIMARY_IMAGE, DEFAULT_HOME_PRIMARY_IMAGE_SPLITTER_PCT, (10.0, 90.0)),
    SplitterId.ANALYSIS_REFERENCE: SplitterPreset(
        SplitterId.ANALYSIS_REFERENCE,
        DEFAULT_HOME_ANALYSIS_REFERENCE_SPLITTER_PCT,
        (10.0, 90.0),
    ),
}


@dataclass(slots=True)
class ManagedSplitter:
    """Small wrapper around a NiceGUI splitter and its preset.

    Args:
        splitter_id: Managed splitter id.
        splitter: NiceGUI splitter instance.
        preset: Factory preset and limits.
    """

    splitter_id: SplitterId
    splitter: Any
    preset: SplitterPreset

    @property
    def value(self) -> float:
        """Return current splitter value as a float."""
        return float(self.splitter.value)

    def set_value(self, value: float) -> float:
        """Set this splitter value and update the NiceGUI element.

        Args:
            value: Requested splitter value.

        Returns:
            The clamped value that was applied.
        """
        applied = self.preset.clamp(value)
        self.splitter.value = applied
        self.splitter.update()
        return applied


class SplitterManager:
    """Manage Home page splitter values and AppConfig synchronization.

    The manager updates ``AppConfig`` in memory only. Persisting the config remains
    explicit: the application saves on shutdown or when the user saves app
    settings. This avoids hidden disk writes during splitter dragging.

    Args:
        app_config: Shared application config.
    """

    def __init__(self, app_config: AppConfig) -> None:
        self._app_config = app_config
        self._splitters: dict[SplitterId, ManagedSplitter] = {}

    def register(self, splitter_id: SplitterId, splitter: Any) -> ManagedSplitter:
        """Register a NiceGUI splitter.

        Args:
            splitter_id: Managed splitter id.
            splitter: NiceGUI splitter instance.

        Returns:
            Managed splitter wrapper.
        """
        preset = HOME_SPLITTER_PRESETS[splitter_id]
        managed = ManagedSplitter(splitter_id=splitter_id, splitter=splitter, preset=preset)
        self._splitters[splitter_id] = managed
        return managed

    def value_for(self, splitter_id: SplitterId) -> float:
        """Return configured startup value for one splitter.

        Args:
            splitter_id: Managed splitter id.

        Returns:
            Configured value clamped to splitter limits.
        """
        preset = HOME_SPLITTER_PRESETS[splitter_id]
        if splitter_id is SplitterId.LEFT_TOOLBAR:
            return preset.clamp(HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT)
        return preset.clamp(self._app_config.get_home_splitter_value(splitter_id.value))

    def set_value(self, splitter_id: SplitterId, value: float, *, remember: bool = True) -> float:
        """Set one splitter value programmatically.

        Args:
            splitter_id: Managed splitter id.
            value: Requested value.
            remember: Whether to update in-memory ``AppConfig``.

        Returns:
            Applied clamped value.
        """
        managed = self._splitters[splitter_id]
        applied = managed.set_value(value)
        if remember:
            self._remember_value(splitter_id, applied)
        return applied

    def capture_current_value(self, splitter_id: SplitterId) -> None:
        """Remember the current UI value for one splitter in AppConfig memory.

        Args:
            splitter_id: Managed splitter id.

        Returns:
            None.
        """
        managed = self._splitters.get(splitter_id)
        if managed is None:
            return
        self._remember_value(splitter_id, managed.value)

    def set_left_toolbar_open(self, is_open: bool) -> None:
        """Set left toolbar splitter to open or closed state.

        Args:
            is_open: True to show the left-toolbar panel, False to collapse to
                icon rail width.

        Returns:
            None.
        """
        if is_open:
            value = self._app_config.get_home_splitter_value(SplitterId.LEFT_TOOLBAR.value)
            if value <= HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT + HOME_LEFT_TOOLBAR_COLLAPSED_SLACK_PCT:
                value = DEFAULT_HOME_LEFT_TOOLBAR_OPEN_SPLITTER_PCT
            self.set_value(SplitterId.LEFT_TOOLBAR, value, remember=False)
        else:
            self.set_value(SplitterId.LEFT_TOOLBAR, HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT, remember=False)

    def reset_all(self) -> None:
        """Reset all managed splitters to factory values.

        Returns:
            None.
        """
        self._app_config.reset_home_splitters()
        for splitter_id in self._splitters:
            if splitter_id is SplitterId.LEFT_TOOLBAR:
                self.set_value(splitter_id, HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT, remember=False)
            else:
                self.set_value(splitter_id, self._app_config.get_home_splitter_value(splitter_id.value), remember=False)

    def _remember_value(self, splitter_id: SplitterId, value: float) -> None:
        """Remember a user-adjusted splitter value in AppConfig memory.

        Args:
            splitter_id: Managed splitter id.
            value: Current splitter value.

        Returns:
            None.
        """
        if splitter_id is SplitterId.LEFT_TOOLBAR:
            if value <= HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT + HOME_LEFT_TOOLBAR_COLLAPSED_SLACK_PCT:
                return
        self._app_config.set_home_splitter_value(splitter_id.value, value)
