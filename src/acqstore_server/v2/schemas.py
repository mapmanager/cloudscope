"""Pydantic request and response schemas for AcqStore Server API v2.

Internal service models intentionally use Python ``snake_case`` names and do
not contain HTTP URLs. This module alone defines the JSON-facing API contract.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base model for strict camelCase API v2 payloads."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra='forbid',
    )


ChannelIndex = Annotated[int, Field(ge=0)]


class _ChannelSelectionRequest(ApiModel):
    """Shared generic channel selection for open requests."""

    channel_indices: list[ChannelIndex] | None = None

    @field_validator('channel_indices')
    @classmethod
    def _validate_channel_indices(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if not value:
            raise ValueError('channelIndices must contain at least one channel index')
        if len(value) != len(set(value)):
            raise ValueError('channelIndices must not contain duplicate indices')
        return value


class OpenRequest(_ChannelSelectionRequest):
    """Request body for opening a server-accessible acquisition path."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra='forbid',
        json_schema_extra={
            'examples': [
                {'path': '/data/example.oir'},
                {'path': '/data/example.tif', 'channelIndices': [1, 0]},
            ]
        },
    )

    path: str = Field(min_length=1, description='Absolute path visible to the local server process.')

    @field_validator('path')
    @classmethod
    def _path_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('path must not be blank')
        return value


class PickAndOpenRequest(_ChannelSelectionRequest):
    """Request body for native file selection followed by opening."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra='forbid',
        json_schema_extra={
            'examples': [
                {},
                {'channelIndices': [0, 1], 'extensions': ['.oir', '.tif']},
            ]
        },
    )

    extensions: list[str] | None = Field(
        default=None,
        description='Optional native file-dialog extension filter.',
    )

    @field_validator('extensions')
    @classmethod
    def _validate_extensions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError('extensions must contain at least one extension')
        normalized: list[str] = []
        for extension in value:
            extension = extension.strip()
            if not extension:
                raise ValueError('extensions must not contain blank values')
            normalized.append(extension if extension.startswith('.') else f'.{extension}')
        if len(normalized) != len(set(normalized)):
            raise ValueError('extensions must not contain duplicate values')
        return normalized


class ApiLinkResponse(ApiModel):
    """One discoverable API v2 resource link."""

    href: str = Field(min_length=1)
    method: Literal['GET', 'POST', 'DELETE']
    description: str = Field(min_length=1)


class ApiIndexResponse(ApiModel):
    """Discoverable entry point for AcqStore Server API v2."""

    ok: Literal[True] = True
    api_version: Literal['v2'] = 'v2'
    description: str
    links: dict[str, ApiLinkResponse]


class BinaryEncodingResponse(ApiModel):
    """Binary transport representation used for served planes."""

    served_dtype: Literal['float32'] = 'float32'
    encoding: Literal['raw-f32-le'] = 'raw-f32-le'
    layout: Literal['row-major'] = 'row-major'
    media_type: Literal['application/octet-stream'] = 'application/octet-stream'


class CapabilitiesResponse(ApiModel):
    """Runtime AcqStore loader and transport capabilities."""

    ok: Literal[True] = True
    api_version: Literal['v2'] = 'v2'
    supported_import_extensions: list[str]
    allowed_import_extensions: list[str]
    binary: BinaryEncodingResponse = Field(default_factory=BinaryEncodingResponse)
    session_ttl_seconds: float = Field(gt=0)


class AxisResponse(ApiModel):
    """Description of one array dimension in a served plane."""

    array_dimension: int = Field(ge=0)
    name: str = Field(min_length=1)
    size: int = Field(gt=0)
    step: float = Field(gt=0)
    unit: str = Field(min_length=1)


class SourceResponse(ApiModel):
    """Source acquisition metadata."""

    path: str
    name: str
    format: str
    source_dtype: str
    num_channels: int = Field(gt=0)



class HeaderResponse(ApiModel):
    """AcqStore image header normalized for JSON clients."""

    shape: list[int]
    dims: list[str]
    sizes: dict[str, int]
    dtype: str
    num_channels: int = Field(gt=0)
    physical_units: list[float | None]
    physical_units_labels: list[str]
    date: str
    time: str
    file_size: str


class PlaneResponse(ApiModel):
    """Encoding and geometry shared by a collection of channel planes."""

    shape: tuple[int, int]
    served_dtype: Literal['float32'] = 'float32'
    encoding: Literal['raw-f32-le'] = 'raw-f32-le'
    layout: Literal['row-major'] = 'row-major'
    axes: list[AxisResponse]

    @field_validator('shape')
    @classmethod
    def _shape_must_be_positive(cls, value: tuple[int, int]) -> tuple[int, int]:
        if any(size <= 0 for size in value):
            raise ValueError('shape dimensions must be positive')
        return value


class ChannelResponse(ApiModel):
    """One generic source channel binary resource."""

    index: ChannelIndex
    name: str
    byte_length: int = Field(gt=0)
    data_url: str


class ScanPathResponse(ApiModel):
    """Reference-image scan path coordinates in AcqStore convention."""

    x: list[float]
    y: list[float]

    @field_validator('y')
    @classmethod
    def _coordinate_lengths_match(cls, value: list[float], info: object) -> list[float]:
        # Pydantic exposes already-validated fields through ValidationInfo.data.
        x = getattr(info, 'data', {}).get('x')
        if x is not None and len(x) != len(value):
            raise ValueError('scan path x and y must contain the same number of coordinates')
        return value


class ReferenceChannelResponse(ApiModel):
    """One generic reference-image channel binary resource."""

    index: ChannelIndex
    byte_length: int = Field(gt=0)
    data_url: str


class ReferenceResponse(ApiModel):
    """Reference image metadata and channel resources."""

    plane: PlaneResponse
    channels: list[ReferenceChannelResponse]
    line_roi: tuple[float, float, float, float] | None = None
    scan_path: ScanPathResponse | None = None


class OpenResponse(ApiModel):
    """Successful API v2 open response."""

    ok: Literal[True] = True
    session_id: str
    source: SourceResponse
    header: HeaderResponse
    plane: PlaneResponse
    channels: list[ChannelResponse]
    reference: ReferenceResponse | None = None


class SessionResponse(ApiModel):
    """Metadata for one live binary session."""

    ok: Literal[True] = True
    session_id: str
    ttl_seconds_remaining: float = Field(ge=0)
    channel_indices: list[ChannelIndex]
    reference_channel_indices: list[ChannelIndex]
    total_bytes: int = Field(ge=0)


class DeleteSessionResponse(ApiModel):
    """Confirmation that a live session was explicitly deleted."""

    ok: Literal[True] = True
    session_id: str
    deleted: Literal[True] = True


class ErrorDetailResponse(ApiModel):
    """One machine-readable request-validation issue."""

    location: list[str]
    message: str
    type: str


class ErrorResponse(ApiModel):
    """Stable API v2 error envelope."""

    ok: Literal[False] = False
    error: str
    message: str
    details: list[ErrorDetailResponse] | None = None
