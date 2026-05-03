"""Analysis plugin registry."""

from __future__ import annotations

from typing import TypeVar

from acqstore.acq_image.analysis.model import BaseAnalysis

AnalysisType = TypeVar("AnalysisType", bound=BaseAnalysis)

_ANALYSIS_REGISTRY: dict[str, type[BaseAnalysis]] = {}


def register_analysis_class(cls: type[AnalysisType]) -> type[AnalysisType]:
    """Register an analysis class.

    Args:
        cls: Analysis class to register. It must define ``analysis_name``.

    Returns:
        The same class, allowing decorator-style registration.

    Raises:
        ValueError: If the class has no name or the name is already registered.
    """
    analysis_name = getattr(cls, "analysis_name", None)
    if not analysis_name:
        raise ValueError(f"{cls.__name__} is missing analysis_name")

    if analysis_name in _ANALYSIS_REGISTRY:
        raise ValueError(f"Duplicate analysis_name: {analysis_name!r}")

    _ANALYSIS_REGISTRY[str(analysis_name)] = cls
    return cls


def get_analysis_class(analysis_name: str) -> type[BaseAnalysis]:
    """Return registered analysis class by name.

    Args:
        analysis_name: Analysis type name.

    Returns:
        Registered analysis class.

    Raises:
        KeyError: If no class is registered for ``analysis_name``.
    """
    return _ANALYSIS_REGISTRY[analysis_name]


def get_analysis_registry() -> dict[str, type[BaseAnalysis]]:
    """Return a copy of the analysis registry.

    Returns:
        Mapping from analysis name to analysis class.
    """
    return dict(_ANALYSIS_REGISTRY)


def clear_analysis_registry() -> None:
    """Clear the registry.

    This is intended for unit tests.

    Returns:
        None.
    """
    _ANALYSIS_REGISTRY.clear()
