"""Exercise the AcqStore analysis API with one hardcoded AcqImage path.

Edit ``SOURCE_PATH`` before running.

Run:

    uv run python scripts/try_acq_analysis.py
"""

from __future__ import annotations

from pathlib import Path

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.analysis import examples  # noqa: F401  # register examples
from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisRunContext

SOURCE_PATH = "/Users/cudmore/Sites/cloudscope/tests/acqstore/data/oir-samples/20251030_A106_0001.oir"


def load_acq_image(path: str) -> AcqImage:
    """Load one acquisition image.

    Args:
        path: Acquisition file path.

    Returns:
        Loaded acquisition image.
    """
    return AcqImage(path)


def get_target(acq_image: AcqImage) -> tuple[int, int]:
    """Return channel and ROI target for test analysis.

    Args:
        acq_image: Acquisition image.

    Returns:
        Tuple ``(channel, roi_id)``.

    Raises:
        RuntimeError: If no default channel or ROI is available.
    """
    channel = acq_image.get_default_channel()
    roi_id = acq_image.get_default_roi()
    if channel is None:
        raise RuntimeError("No default channel available")
    if roi_id is None:
        raise RuntimeError("No default ROI available")
    return channel, roi_id


def run_velocity_analysis(acq_image: AcqImage, channel: int, roi_id: int) -> None:
    """Create and run velocity analysis.

    Args:
        acq_image: Acquisition image.
        channel: Channel index.
        roi_id: ROI identifier.

    Returns:
        None.
    """
    analysis = acq_image.analysis.create(
        "velocity",
        channel=channel,
        roi_id=roi_id,
    )

    context = AnalysisRunContext(
        progress_callback=lambda fraction, message: print(f"velocity {fraction}: {message}")
    )
    acq_image.analysis.run_analysis(analysis.key, context=context)


def run_velocity_event_analysis(acq_image: AcqImage, channel: int, roi_id: int) -> None:
    """Create and run velocity-event analysis.

    Args:
        acq_image: Acquisition image.
        channel: Channel index.
        roi_id: ROI identifier.

    Returns:
        None.
    """
    analysis = acq_image.analysis.create(
        "velocity_event",
        channel=channel,
        roi_id=roi_id,
    )
    acq_image.analysis.run_analysis(analysis.key)


def save_acq_image(acq_image: AcqImage) -> None:
    """Save acquisition image sidecars.

    Args:
        acq_image: Acquisition image to save.

    Returns:
        None.
    """
    acq_image.save()


def reload_acq_image(path: str) -> AcqImage:
    """Reload an acquisition image from disk.

    Args:
        path: Acquisition file path.

    Returns:
        Reloaded acquisition image.
    """
    return AcqImage(path)


def print_analysis_summary(acq_image: AcqImage) -> None:
    """Print loaded analysis records and table columns.

    Args:
        acq_image: Acquisition image.

    Returns:
        None.
    """
    print("Analysis records:")
    for record in acq_image.analysis.serialize_json_analysis():
        print(record)

    for analysis in acq_image.analysis.as_list():
        print(
            analysis.key,
            "summary=",
            analysis.result.summary,
            "columns=",
            analysis.get_table_columns(),
        )


def main() -> None:
    """Run load -> analysis -> save -> reload workflow.

    Returns:
        None.
    """
    path = str(Path(SOURCE_PATH).expanduser())
    acq_image = load_acq_image(path)
    channel, roi_id = get_target(acq_image)

    run_velocity_analysis(acq_image, channel, roi_id)
    run_velocity_event_analysis(acq_image, channel, roi_id)
    save_acq_image(acq_image)

    reloaded = reload_acq_image(path)
    print_analysis_summary(reloaded)


if __name__ == "__main__":
    main()
