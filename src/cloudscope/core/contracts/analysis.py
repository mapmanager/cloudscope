"""Analysis contract for one acquisition file."""

from __future__ import annotations

from typing import Any, Protocol

from .common import AnalysisKind


class AcqAnalysisProtocol(Protocol):
    """Backend-facing analysis surface for one acquisition file."""

    def supports(self, kind: AnalysisKind) -> bool:
        """Return whether an analysis kind is supported.

        Args:
            kind: Analysis kind to query.

        Returns:
            ``True`` when the backend supports the requested analysis kind.
        """

    def has_result(
        self,
        kind: AnalysisKind,
        channel: int | None = None,
        roi_id: int | None = None,
    ) -> bool:
        """Return whether a result already exists for the requested scope.

        Args:
            kind: Analysis kind to query.
            channel: Optional backend-native channel index.
            roi_id: Optional stable ROI identifier.

        Returns:
            ``True`` when a result exists for the requested scope.
        """

    def get_result(
        self,
        kind: AnalysisKind,
        channel: int | None = None,
        roi_id: int | None = None,
    ) -> Any | None:
        """Return an existing analysis result for the requested scope.

        Args:
            kind: Analysis kind to fetch.
            channel: Optional backend-native channel index.
            roi_id: Optional stable ROI identifier.

        Returns:
            Backend-defined analysis result object, or ``None`` when no result is
            available.
        """

    def run(
        self,
        kind: AnalysisKind,
        channel: int | None = None,
        roi_id: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Run analysis and return the resulting backend-defined object.

        Args:
            kind: Analysis kind to run.
            channel: Optional backend-native channel index.
            roi_id: Optional stable ROI identifier.
            **kwargs: Backend-specific analysis options.

        Returns:
            Backend-defined analysis result object.

        Raises:
            NotImplementedError: If the backend does not support the requested
                analysis kind.
            ValueError: If the provided scope or options are invalid.
        """
