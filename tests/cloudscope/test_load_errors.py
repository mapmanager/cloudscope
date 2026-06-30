"""Tests for cloudscope.utils.load_errors."""

from __future__ import annotations

from cloudscope.utils.load_errors import format_raster_load_error


class _ImageStub:
    """Minimal acq-image stand-in for load-error formatting tests."""

    name = "20220608_cell11.tif"
    file_id = "/data/20220608_cell11.tif"


def test_format_raster_load_error_short_notify_for_missing_channel_axis() -> None:
    """Missing C axis errors should produce a compact toast message."""
    exc = ValueError(
        "Cannot slice ch 0 from '/data/20220608_cell11.tif': num_channels=2, "
        "dims=('Y', 'X'), loaded shape (1000, 443), no C axis "
        "(Olympus split-channel siblings may be missing)."
    )

    presentation = format_raster_load_error(
        exc,
        acq_image=_ImageStub(),  # type: ignore[arg-type]
        channel=0,
        operation="Primary image",
    )

    assert presentation.notify_message == (
        "20220608_cell11.tif (ch 0): 2 channels in header, image has no C axis"
    )
    assert "Primary image load failed for 20220608_cell11.tif" in presentation.log_message
    assert "file_id='/data/20220608_cell11.tif'" in presentation.log_message
    assert "num_channels=2" in presentation.log_message


def test_format_raster_load_error_truncates_long_unknown_errors() -> None:
    """Unknown long errors should truncate for notify but stay full in log."""

    class _SampleStub:
        name = "sample.tif"
        file_id = "/tmp/sample.tif"

    exc = ValueError("x" * 200)
    presentation = format_raster_load_error(
        exc,
        acq_image=_SampleStub(),  # type: ignore[arg-type]
        channel=1,
        operation="Reference image",
    )

    assert presentation.notify_message.startswith("sample.tif (ch 1): ")
    assert len(presentation.notify_message) < 160
    assert str(exc) in presentation.log_message
