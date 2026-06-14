"""Generate markdown schema tables for the MkDocs site (dev helper).

This script is a development helper. It is not used at runtime, by the
CloudScope app, or by example notebooks. It writes one markdown page per
schema under ``docs/schemas/`` (overwriting existing files) and prints each
table to the console.

Markdown is produced from pandas DataFrames via ``DataFrame.to_markdown``,
which requires the ``tabulate`` package.

Run:

    uv run python scripts/docs/generate_schema.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
from acqstore.acq_image.analysis.heart_rate_analysis.heart_rate_analysis import HeartRateAnalysis
from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import RadonVelocityAnalysis
from acqstore.acq_image.metadata import (
    EXPERIMENT_METADATA_SCHEMA,
    IMAGE_HEADER_METADATA_SCHEMA,
)
from acqstore.schema import FieldSchema

_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "schemas"


def _field_schema_dataframe(fields: tuple[FieldSchema, ...]) -> pd.DataFrame:
    """Return a DataFrame describing metadata ``FieldSchema`` entries.

    Args:
        fields: Metadata schema fields to document.

    Returns:
        DataFrame indexed by parameter ``name``.
    """
    columns = [
        "name",
        "display_name",
        "type",
        "default",
        "unit",
        "choices",
        "editable",
        "group",
        "description",
    ]
    rows = [
        {
            "name": field.name,
            "display_name": field.display_name,
            "type": field.value_type.value,
            "default": field.default_value,
            "unit": field.unit,
            "choices": field.choices,
            "editable": field.editable,
            "group": field.group,
            "description": field.description,
        }
        for field in fields
    ]
    return pd.DataFrame(rows, columns=columns).set_index("name")


def _write(title: str, filename: str, df: pd.DataFrame) -> None:
    """Write one schema markdown page and print it to the console.

    Args:
        title: Page heading text.
        filename: Output filename under ``docs/schemas/``.
        df: Schema DataFrame to render.
    """
    document = f"# {title}\n\n{df.to_markdown()}\n"
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _OUTPUT_DIR / filename
    out_path.write_text(document, encoding="utf-8")
    print(document)
    print(f"Wrote {out_path}\n")


def main() -> None:
    """Generate all schema markdown pages under ``docs/schemas/``."""
    _write(
        "Experiment Metadata",
        "experimental_metadata.md",
        _field_schema_dataframe(EXPERIMENT_METADATA_SCHEMA.fields),
    )
    _write(
        "Image Header Metadata",
        "header_metadata.md",
        _field_schema_dataframe(IMAGE_HEADER_METADATA_SCHEMA.fields),
    )
    _write(
        "Velocity Detection Parameters",
        "velocity_detection_parameters.md",
        RadonVelocityAnalysis.get_detection_schema_dataframe(),
    )
    _write(
        "Diameter Detection Parameters",
        "diameter_detection_parameters.md",
        DiameterAnalysis.get_detection_schema_dataframe(),
    )
    _write(
        "Event Detection Parameters",
        "event_detection_parameters.md",
        EventAnalysis.get_detection_schema_dataframe(),
    )
    _write(
        "Heart Rate Detection Parameters",
        "heart_rate_detection_parameters.md",
        HeartRateAnalysis.get_detection_schema_dataframe(),
    )


if __name__ == "__main__":
    main()
