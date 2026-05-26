"""Run diameter batch analysis from hardcoded file paths.

Edit the constants near the top of the file before running.

Run:

    uv run python scripts/acqstore/try_diameter_batch.py
"""

from __future__ import annotations

from pathlib import Path

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.analysis.batch.acq_analysis_batch import AcqAnalysisBatch
from acqstore.acq_image.analysis.batch.diameter_batch_strategy import DiameterBatchStrategy
from acqstore.acq_image.analysis.batch.roi_mode import RoiBatchMode
from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis

SOURCE_PATHS = [
    "/path/to/file1.oir",
    "/path/to/file2.oir",
]
CHANNEL = 0
ROI_MODE = RoiBatchMode.ANALYZE_EXISTING_ROI
ROI_ID: int | None = 1
MAX_PARALLEL_FILES = 2
USE_THREADS = True
MAX_WORKERS: int | None = None


def load_acq_images(paths: list[str]) -> list[AcqImage]:
    """Load acquisition images.

    Args:
        paths: Acquisition file paths.

    Returns:
        Loaded acquisition images.
    """
    return [AcqImage(str(Path(path).expanduser())) for path in paths]


def build_detection_params() -> dict[str, object]:
    """Build validated diameter detection parameters.

    Returns:
        Validated detection parameter dictionary.
    """
    params = DiameterAnalysis.get_default_detection_params()
    DiameterAnalysis.validate_detection_params(params)
    return params


def run_batch(acq_images: list[AcqImage]) -> None:
    """Run diameter batch analysis and optionally save OK files.

    Args:
        acq_images: Acquisition images to analyze.

    Returns:
        None.
    """
    strategy = DiameterBatchStrategy(
        channel=CHANNEL,
        roi_mode=ROI_MODE,
        roi_id=ROI_ID,
        detection_params=build_detection_params(),
        use_threads=USE_THREADS,
        max_workers=MAX_WORKERS,
    )
    batch = AcqAnalysisBatch(
        acq_images,
        strategy,
        max_parallel_files=MAX_PARALLEL_FILES,
    )
    batch.run(on_file_result=lambda result: print(result))

    # Save explicitly here when desired, for example:
    # for acq_image in acq_images:
    #     acq_image.save()


def main() -> None:
    """Run the manual diameter batch workflow.

    Returns:
        None.
    """
    acq_images = load_acq_images(SOURCE_PATHS)
    run_batch(acq_images)


if __name__ == "__main__":
    main()
