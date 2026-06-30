"""Format user-visible and log messages for image load failures."""

from __future__ import annotations

import re
from dataclasses import dataclass

from acqstore.acq_image.acq_image import AcqImage

_NOTIFY_TRUNCATE = 120


@dataclass(frozen=True, slots=True)
class LoadErrorPresentation:
    """Short toast text and a fuller line for ``logger.exception``."""

    notify_message: str
    log_message: str


def _short_notify_detail(exc: BaseException) -> str:
    """Return a compact summary of ``exc`` suitable for ``ui.notify``."""
    text = str(exc).strip()
    if not text:
        return "load failed"

    lower = text.lower()
    if "no c axis" in lower:
        match = re.search(r"num_channels=(\d+)", text)
        if match is not None and int(match.group(1)) > 1:
            return f"{match.group(1)} channels in header, image has no C axis"
        return "image has no C axis"

    first_line = text.splitlines()[0]
    if len(first_line) <= _NOTIFY_TRUNCATE:
        return first_line
    return first_line[: _NOTIFY_TRUNCATE - 3] + "..."


def format_raster_load_error(
    exc: BaseException,
    *,
    acq_image: AcqImage | None,
    channel: int | None,
    operation: str,
) -> LoadErrorPresentation:
    """Build short notify and descriptive log strings for raster load failures.

    Args:
        exc: Raised exception from plane or reference load.
        acq_image: Acquisition object for the selected file, if any.
        channel: Selected channel index, if any.
        operation: Human-readable operation label, e.g. ``"Primary image"``.

    Returns:
        Presentation with ``notify_message`` for toasts and ``log_message`` for
        ``logger.exception``.
    """
    name = acq_image.name if acq_image is not None else "image"
    file_id = acq_image.file_id if acq_image is not None else None
    detail = _short_notify_detail(exc)

    if channel is not None:
        notify_message = f"{name} (ch {channel}): {detail}"
    else:
        notify_message = f"{name}: {detail}"

    if channel is not None and file_id is not None:
        context = f" (channel {channel}, file_id={file_id!r})"
    elif file_id is not None:
        context = f" (file_id={file_id!r})"
    else:
        context = ""

    log_message = f"{operation} load failed for {name}{context}: {exc}"
    return LoadErrorPresentation(
        notify_message=notify_message,
        log_message=log_message,
    )
