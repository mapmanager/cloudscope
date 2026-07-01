"""Tests for kymograph plot axis label helpers."""

from __future__ import annotations

from cloudscope.plot_axis_labels import kymograph_time_x_label


class _HeaderSection:
    def __init__(self, label_y: object) -> None:
        self._label_y = label_y

    def get_values(self) -> dict[str, object]:
        return {'physical_label_y': self._label_y}


class _AcqImage:
    def __init__(self, label_y: object) -> None:
        self._label_y = label_y

    def get_metadata_section(self, section_id: str) -> _HeaderSection:
        assert section_id == 'acq_image_header'
        return _HeaderSection(self._label_y)


def test_kymograph_time_x_label_uses_header_when_non_empty() -> None:
    assert kymograph_time_x_label(_AcqImage('seconds'), fallback='Time (s)') == 'seconds'


def test_kymograph_time_x_label_falls_back_when_header_empty() -> None:
    assert kymograph_time_x_label(_AcqImage(''), fallback='Time (s)') == 'Time (s)'


def test_kymograph_time_x_label_falls_back_when_no_image() -> None:
    assert kymograph_time_x_label(None, fallback='Time (s)') == 'Time (s)'
