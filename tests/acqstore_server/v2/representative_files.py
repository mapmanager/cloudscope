"""Deterministic transport-neutral acquisition fixtures for API v2 tests.

The filename is retained so existing replacement merges overwrite Ticket 010's
optional real-file helper. These fixtures do not invoke AcqStore loaders.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from acqstore_server.v2.models import (
    AcquisitionHeader,
    AxisInfo,
    ChannelPlane,
    OpenedAcquisition,
)


def opened_acquisition_fixture(
    path: str,
    *,
    format_name: str = 'synthetic',
    channel_indices: tuple[int, ...] = (0, 1),
    shape: tuple[int, int] = (5, 4),
) -> OpenedAcquisition:
    """Build a known-good service result without testing file decoding."""
    channels = tuple(
        ChannelPlane(
            index=index,
            name=f'Channel {index}',
            source_dtype='uint16',
            array=(
                np.arange(shape[0] * shape[1], dtype=np.uint16).reshape(shape)
                + index * 100
            ),
        )
        for index in channel_indices
    )
    return OpenedAcquisition(
        path=Path(path),
        format=format_name,
        source_dtype='uint16',
        num_source_channels=max(channel_indices, default=-1) + 1,
        header=AcquisitionHeader(
            shape=(len(channel_indices), *shape),
            dims=('C', 'Y', 'X'),
            sizes={'C': len(channel_indices), 'Y': shape[0], 'X': shape[1]},
            dtype='uint16',
            num_channels=len(channel_indices),
            physical_units=(1.0, 0.002, 0.5),
            physical_units_labels=('Channels', 'seconds', 'micrometer'),
            date='',
            time='',
            file_size='',
        ),
        axes=(
            AxisInfo(
                array_dimension=0,
                name='Y',
                size=shape[0],
                step=0.002,
                unit='seconds',
            ),
            AxisInfo(
                array_dimension=1,
                name='X',
                size=shape[1],
                step=0.5,
                unit='micrometer',
            ),
        ),
        channels=channels,
        reference=None,
    )
