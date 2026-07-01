"""Plot axis label helpers for CloudScope analysis views."""

from __future__ import annotations

from acqstore.acq_image.acq_image import AcqImage

_IMAGE_HEADER_SECTION_ID = 'acq_image_header'


def kymograph_time_x_label(acq_image: AcqImage | None, *, fallback: str) -> str:
    """Return the x-axis label for time-series kymograph plots.

    Uses the image header ``physical_label_y`` when non-empty; otherwise returns
    ``fallback`` (typically analysis ``plot_data.x_label``).

    Args:
        acq_image: Selected acquisition image, or ``None``.
        fallback: Label to use when header metadata is unavailable.

    Returns:
        X-axis label string.
    """
    if acq_image is None:
        return fallback
    try:
        section = acq_image.get_metadata_section(_IMAGE_HEADER_SECTION_ID)
        label = str(section.get_values()['physical_label_y']).strip()
    except (AttributeError, KeyError, TypeError, ValueError):
        return fallback
    return label if label else fallback
