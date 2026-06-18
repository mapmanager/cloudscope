"""Shared per-session CloudScope runtime for multi-page NiceGUI clients."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from cloudscope.app_config import AppConfig
from cloudscope.controllers.analysis_controller import AnalysisController
from cloudscope.controllers.event_analysis_controller import EventAnalysisController
from cloudscope.controllers.home_page_controller import HomePageController, HomePageState
from cloudscope.controllers.load_save_controller import LoadSaveController
from cloudscope.controllers.roi_controller import RoiController
from cloudscope.controllers.velocity_pool_controller import VelocityPoolController
from cloudscope.event_bus import EventBus
from cloudscope.events.files import LoadPathIntent, LoadPathKind
from cloudscope.task_runner import TaskRunner
from cloudscope.user_context import (
    UserContext,
    get_or_create_demo_session_id,
    resolve_user_context_from_env,
)


def infer_load_kind(path: str) -> LoadPathKind:
    """Infer load kind from a filesystem path string.

    Args:
        path: Path to a file, folder, or CSV list.

    Returns:
        Matching ``LoadPathKind`` for ``LoadPathIntent``.
    """
    if path.lower().endswith('.csv'):
        return LoadPathKind.CSV
    return LoadPathKind.FOLDER if Path(path).expanduser().is_dir() else LoadPathKind.FILE


@dataclass(slots=True)
class CloudScopeRuntime:
    """Shared application runtime for one user or browser session.

    Owns canonical in-memory scientific state, controllers, and the event bus.
    NiceGUI pages create UI views only and read state from this object.

    Args:
        user_context: Resolved workspace/user context.
        app_config: Application configuration for this context.
        event_bus: Shared typed event bus.
        home_page_controller: Controller owning ``HomePageState``.
        load_save_controller: Load and save workflow controller.
        analysis_controller: Analysis workflow controller.
        roi_controller: ROI mutation controller.
        event_analysis_controller: Event-analysis controller.
        velocity_pool_controller: Velocity pool synchronization controller.
        task_runner: Background task runner for long-running work.
        initialized: Whether one-time bootstrap has completed.
        controllers_bound: Whether controller ``bind()`` has run.
    """

    user_context: UserContext
    app_config: AppConfig
    event_bus: EventBus
    home_page_controller: HomePageController
    load_save_controller: LoadSaveController
    analysis_controller: AnalysisController
    roi_controller: RoiController
    event_analysis_controller: EventAnalysisController
    velocity_pool_controller: VelocityPoolController
    task_runner: TaskRunner
    initialized: bool = False
    controllers_bound: bool = False

    @property
    def app_state(self) -> HomePageState:
        """Return shared home-page application state.

        Returns:
            Current ``HomePageState`` owned by ``home_page_controller``.
        """
        return self.home_page_controller.state

    def ensure_controllers_bound(self) -> None:
        """Bind runtime controllers to the shared event bus once.

        Returns:
            None.
        """
        if self.controllers_bound:
            return
        self.home_page_controller.bind()
        self.load_save_controller.bind()
        self.analysis_controller.bind()
        self.roi_controller.bind()
        self.event_analysis_controller.bind()
        self.velocity_pool_controller.bind()
        self.controllers_bound = True

    def initialize_once(self) -> None:
        """Run one-time bootstrap for this runtime instance.

        Idempotent: does not reload ``AcqImageList`` or repeat bootstrap when
        the runtime already holds loaded state or has been initialized.

        Returns:
            None.
        """
        self.ensure_controllers_bound()
        if self.initialized:
            return
        if self.home_page_controller.state.acq_image_list is not None:
            self.initialized = True
            return

        self.home_page_controller.load_demo_files([])
        last_path = self.app_config.get_last_path().strip()
        if last_path:
            self.event_bus.publish(
                LoadPathIntent(path=last_path, kind=infer_load_kind(last_path))
            )
        self.initialized = True


class CloudScopeRuntimeRegistry:
    """Thread-safe registry of per-session ``CloudScopeRuntime`` instances."""

    def __init__(self) -> None:
        """Initialize an empty runtime registry."""
        self._lock = threading.RLock()
        self._runtimes: dict[str, CloudScopeRuntime] = {}

    def get_or_create(self, key: str, factory: Callable[[], CloudScopeRuntime]) -> CloudScopeRuntime:
        """Return an existing runtime or create one with ``factory``.

        Args:
            key: Stable per-user or per-session runtime key.
            factory: Callable returning a new ``CloudScopeRuntime``.

        Returns:
            Shared runtime for ``key``.
        """
        with self._lock:
            runtime = self._runtimes.get(key)
            if runtime is None:
                runtime = factory()
                self._runtimes[key] = runtime
            return runtime

    def get(self, key: str) -> CloudScopeRuntime | None:
        """Return a runtime for ``key`` when present.

        Args:
            key: Stable per-user or per-session runtime key.

        Returns:
            Registered runtime, or ``None`` when absent.
        """
        with self._lock:
            return self._runtimes.get(key)

    def clear(self) -> None:
        """Remove all registered runtimes.

        Returns:
            None.
        """
        with self._lock:
            self._runtimes.clear()


_registry: CloudScopeRuntimeRegistry | None = None


def get_registry() -> CloudScopeRuntimeRegistry:
    """Return the process-wide runtime registry.

    Returns:
        Shared ``CloudScopeRuntimeRegistry`` instance.
    """
    global _registry
    if _registry is None:
        _registry = CloudScopeRuntimeRegistry()
    return _registry


def reset_runtime_registry_for_tests() -> None:
    """Clear the process-wide runtime registry.

    For unit tests only.

    Returns:
        None.
    """
    global _registry
    if _registry is not None:
        _registry.clear()
    _registry = None


def runtime_key_from_user_context(user_context: UserContext) -> str:
    """Return the registry key for a resolved user context.

    Args:
        user_context: Resolved CloudScope user context.

    Returns:
        Stable runtime key, currently ``user_context.user_id``.
    """
    return user_context.user_id


def resolve_runtime_context() -> tuple[UserContext, AppConfig]:
    """Resolve user context and app config for the current NiceGUI client.

    Returns:
        Tuple of ``(UserContext, AppConfig)`` for the active session.
    """
    demo_session_id = get_or_create_demo_session_id()
    user_context = resolve_user_context_from_env(demo_session_id=demo_session_id)
    app_config = user_context.load_app_config(create_if_missing=False)
    return user_context, app_config


def _build_runtime(user_context: UserContext, app_config: AppConfig) -> CloudScopeRuntime:
    """Construct a new runtime for one user/session.

    Args:
        user_context: Resolved user context.
        app_config: Application configuration.

    Returns:
        New, uninitialized ``CloudScopeRuntime``.
    """
    event_bus = EventBus()
    home_page_controller = HomePageController(event_bus=event_bus)
    task_runner = TaskRunner(event_bus=event_bus)
    load_save_controller = LoadSaveController(
        event_bus=event_bus,
        home_controller=home_page_controller,
        app_config=app_config,
        user_context=user_context,
        task_runner=task_runner,
    )
    return CloudScopeRuntime(
        user_context=user_context,
        app_config=app_config,
        event_bus=event_bus,
        home_page_controller=home_page_controller,
        load_save_controller=load_save_controller,
        analysis_controller=AnalysisController(
            event_bus=event_bus,
            home_controller=home_page_controller,
            task_runner=task_runner,
        ),
        roi_controller=RoiController(
            event_bus=event_bus,
            home_page_controller=home_page_controller,
        ),
        event_analysis_controller=EventAnalysisController(
            event_bus=event_bus,
            home_controller=home_page_controller,
        ),
        velocity_pool_controller=VelocityPoolController(
            event_bus=event_bus,
            home_controller=home_page_controller,
        ),
        task_runner=task_runner,
    )


def get_current_runtime() -> CloudScopeRuntime:
    """Return the shared runtime for the current user/session.

    Returns:
        Shared ``CloudScopeRuntime`` for the active NiceGUI client context.
    """
    user_context, app_config = resolve_runtime_context()
    key = runtime_key_from_user_context(user_context)
    return get_registry().get_or_create(
        key,
        lambda: _build_runtime(user_context, app_config),
    )
