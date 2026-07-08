"""Sweep data models for trace acquisitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from acqstore.acq_trace.epoch_data import EpochTable


@dataclass(frozen=True)
class SweepData:
    """Numeric data for one channel/sweep pair.

    Args:
        sweep_index: Zero-based sweep index.
        channel_index: Zero-based channel index.
        time_sec: Time axis in seconds.
        values: Recorded voltage/current values.
        value_units: Units for ``values``.
        command_values: Command waveform values, if available.
        command_units: Units for ``command_values``.
        epoch_index_values: Integer epoch label for each sample.
        epoch_table: Epoch interval table for the sweep.
    """

    sweep_index: int
    channel_index: int
    time_sec: npt.NDArray[np.floating[Any]]
    values: npt.NDArray[np.floating[Any]]
    value_units: str
    command_values: npt.NDArray[np.floating[Any]] | None
    command_units: str
    epoch_index_values: npt.NDArray[np.int_]
    epoch_table: EpochTable

    def __post_init__(self) -> None:
        """Validate array lengths and indices after construction.

        Raises:
            ValueError: If indices are negative or arrays have inconsistent
                lengths.
        """
        if self.sweep_index < 0:
            raise ValueError(f'sweep_index must be >= 0, got {self.sweep_index}')
        if self.channel_index < 0:
            raise ValueError(f'channel_index must be >= 0, got {self.channel_index}')
        n = len(self.time_sec)
        if len(self.values) != n:
            raise ValueError(
                'values length must match time_sec length, '
                f'got {len(self.values)} and {n}'
            )
        if self.command_values is not None and len(self.command_values) != n:
            raise ValueError(
                'command_values length must match time_sec length, '
                f'got {len(self.command_values)} and {n}'
            )
        if len(self.epoch_index_values) != n:
            raise ValueError(
                'epoch_index_values length must match time_sec length, '
                f'got {len(self.epoch_index_values)} and {n}'
            )

    @property
    def num_samples(self) -> int:
        """Return the number of samples in this sweep.

        Returns:
            Length of the time/value arrays.
        """
        return int(len(self.time_sec))
