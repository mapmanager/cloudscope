"""Epoch data models for sweep-based trace acquisitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class EpochInterval:
    """One command epoch interval for a sweep.

    Args:
        epoch_index: Zero-based epoch index in the source sweep.
        start_sample: Inclusive start sample index.
        end_sample: Exclusive end sample index.
        level: Command level reported by the source file.
        epoch_type: Source-specific epoch type label.
        digital_states: Digital output states associated with the epoch.

    Raises:
        ValueError: If sample bounds are negative or empty.
    """

    epoch_index: int
    start_sample: int
    end_sample: int
    level: float
    epoch_type: str
    digital_states: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """Validate interval bounds after dataclass construction.

        Raises:
            ValueError: If sample bounds are negative or empty.
        """
        if self.epoch_index < 0:
            raise ValueError(f'epoch_index must be >= 0, got {self.epoch_index}')
        if self.start_sample < 0:
            raise ValueError(f'start_sample must be >= 0, got {self.start_sample}')
        if self.end_sample <= self.start_sample:
            raise ValueError(
                'end_sample must be greater than start_sample, '
                f'got start={self.start_sample} end={self.end_sample}'
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dictionary representation.

        Returns:
            Dictionary with JSON-friendly epoch interval values.
        """
        return {
            'epoch_index': self.epoch_index,
            'start_sample': self.start_sample,
            'end_sample': self.end_sample,
            'level': self.level,
            'epoch_type': self.epoch_type,
            'digital_states': list(self.digital_states),
        }


@dataclass(frozen=True)
class EpochTable:
    """Collection of epoch intervals for one sweep.

    Args:
        intervals: Epoch intervals in source-file order.
    """

    intervals: tuple[EpochInterval, ...]

    def __len__(self) -> int:
        """Return the number of epoch intervals.

        Returns:
            Number of intervals in this table.
        """
        return len(self.intervals)

    def to_sample_labels(self, num_samples: int, *, fill_value: int = -1) -> npt.NDArray[np.int_]:
        """Return one integer epoch label per sample.

        Args:
            num_samples: Number of samples in the target sweep.
            fill_value: Label used for samples outside any epoch interval.

        Returns:
            Integer array of shape ``(num_samples,)``. Samples covered by an
            interval receive that interval's ``epoch_index``.

        Raises:
            ValueError: If ``num_samples`` is negative or any interval extends
                beyond the requested sample count.
        """
        if num_samples < 0:
            raise ValueError(f'num_samples must be >= 0, got {num_samples}')
        labels = np.full(num_samples, fill_value, dtype=int)
        for interval in self.intervals:
            if interval.end_sample > num_samples:
                raise ValueError(
                    'epoch interval extends beyond sweep samples: '
                    f'end_sample={interval.end_sample}, num_samples={num_samples}'
                )
            labels[interval.start_sample : interval.end_sample] = interval.epoch_index
        return labels

    def to_dicts(self) -> list[dict[str, Any]]:
        """Return epoch intervals as dictionaries.

        Returns:
            List of JSON-friendly interval dictionaries.
        """
        return [interval.to_dict() for interval in self.intervals]
