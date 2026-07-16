"""Request/response shapes for AcqStore Server HTTP API v1."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class OpenRequest(TypedDict, total=False):
    """Body for ``POST /api/v1/open`` and optional overrides for pick-and-open."""

    path: str
    calciumChannel: int
    vesselChannel: int | None
    extensions: list[str]


class ChannelMeta(TypedDict):
    """One channel plane in an open response."""

    index: int
    name: str
    role: Literal['calcium', 'vessels']
    encoding: Literal['raw-f32-le']
    layout: Literal['row-major']
    height: int
    width: int
    byteLength: int
    url: str


class SourceMeta(TypedDict):
    """Source file metadata in an open response."""

    path: str
    format: str
    numChannels: int
    width: int
    height: int
    dtype: str


class CalibrationMeta(TypedDict):
    """Physical scaling for HTML clients plus header-faithful plane axes.

    HTML-facing aliases (``msPerLine``, ``umPerPixel``, ``stepYSeconds``,
    ``stepXUm``) stay stable for the calcium analyzer. Additive
    ``dim_0_*`` / ``dim_1_*`` fields expose the served 2-D plane steps and
    physical unit labels from the AcqImage header (dim0 = rows/Y, dim1 =
    columns/X).
    """

    msPerLine: float
    umPerPixel: float
    stepYSeconds: float
    stepXUm: float
    unitsSource: Literal['acqimage']
    dim_0_step: float
    dim_1_step: float
    dim_0_units: str
    dim_1_units: str


class ChannelsMeta(TypedDict, total=False):
    """Role-keyed channel metadata. ``vessels`` omitted when single-channel."""

    calcium: ChannelMeta
    vessels: ChannelMeta


class ScanPathMeta(TypedDict):
    """Plot-ready scan path in reference-image pixel coordinates."""

    x: list[float]
    y: list[float]


class ReferenceChannelMeta(TypedDict):
    """One reference-image channel plane plus binary URL."""

    index: int
    encoding: Literal['raw-f32-le']
    layout: Literal['row-major']
    height: int
    width: int
    byteLength: int
    url: str
    dx: float
    dy: float
    xUnit: str
    yUnit: str


class ReferenceMeta(TypedDict):
    """Reference/overview image metadata plus per-channel plane URLs.

    Shared ``lineRoi`` / ``scanPath`` apply to every channel plane.
    Top-level ``height`` / ``width`` / ``byteLength`` / spacing fields summarize
    channel ``0`` (all channels share H×W). Fetch planes via ``channels[i].url``.
    """

    numChannels: int
    encoding: Literal['raw-f32-le']
    layout: Literal['row-major']
    height: int
    width: int
    byteLength: int
    channels: list[ReferenceChannelMeta]
    lineRoi: list[float] | None
    scanPath: ScanPathMeta | None
    dx: float
    dy: float
    xUnit: str
    yUnit: str


class OpenSuccess(TypedDict):
    """Successful open / pick-and-open payload."""

    ok: Literal[True]
    sessionId: str
    source: SourceMeta
    calibration: CalibrationMeta
    channels: ChannelsMeta
    reference: ReferenceMeta | None


class ErrorBody(TypedDict, total=False):
    """Error payload used by API handlers."""

    ok: Literal[False]
    error: str
    message: str


def error_body(error: str, message: str) -> dict[str, Any]:
    """Build a JSON-serializable error object.

    Args:
        error: Stable machine-readable error code.
        message: Human-readable detail.

    Returns:
        Dict with ``ok`` false plus ``error`` and ``message``.
    """
    return {'ok': False, 'error': error, 'message': message}
