"""Print and save markdown documentation tables for AcqStore schemas.

Generates copy/paste-ready markdown tables for the MkDocs site, covering:

- Experiment metadata schema
- Image header metadata schema
- Velocity (Radon) detection parameters
- Diameter detection parameters

Each table is printed to the console and saved as a standalone markdown page
under ``docs/schemas/`` (existing files are overwritten). Every page includes a
generated-on timestamp and the project version read from ``pyproject.toml``.

Run:

    uv run python scripts/acqstore/try_schema_docs.py
"""

from __future__ import annotations

import tomllib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import RadonVelocityAnalysis
from acqstore.acq_image.metadata import (
    EXPERIMENT_METADATA_SCHEMA,
    IMAGE_HEADER_METADATA_SCHEMA,
)
from acqstore.schema_docs import SchemaField, generate_markdown_table

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OUTPUT_DIR = _REPO_ROOT / 'docs' / 'schemas'


def _read_version() -> str:
    """Return the project version from ``pyproject.toml``.

    Returns:
        The ``[project].version`` string.

    Raises:
        KeyError: If the version is not declared in ``pyproject.toml``.
    """
    pyproject = _REPO_ROOT / 'pyproject.toml'
    with pyproject.open('rb') as handle:
        data = tomllib.load(handle)
    return str(data['project']['version'])


def _footer(version: str, *, timestamp: datetime) -> str:
    """Return the italic generated-on/version caption.

    Args:
        version: Project version string.
        timestamp: Generation time.

    Returns:
        A single italic markdown line.
    """
    stamp = timestamp.strftime('%y%m%d %H:%M:%S')
    return f'*Generated on {stamp} \u00b7 cloudscope v{version}*'


def _build_document(
    title: str,
    fields: Sequence[SchemaField],
    *,
    version: str,
    timestamp: datetime,
) -> str:
    """Build a standalone markdown page for one schema.

    Args:
        title: Page heading text.
        fields: Schema fields to document.
        version: Project version string.
        timestamp: Generation time.

    Returns:
        Markdown document with a heading, table, and footer.
    """
    table = generate_markdown_table(fields, print_markdown=False)
    footer = _footer(version, timestamp=timestamp)
    return f'# {title}\n\n{table}\n\n{footer}\n'


def main() -> None:
    """Print and save all four schema tables to ``docs/schemas/``."""
    version = _read_version()
    timestamp = datetime.now()
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    specs: tuple[tuple[str, str, Sequence[SchemaField]], ...] = (
        ('Experiment Metadata', 'experimental_metadata.md', EXPERIMENT_METADATA_SCHEMA.fields),
        ('Image Header Metadata', 'header_metadata.md', IMAGE_HEADER_METADATA_SCHEMA.fields),
        ('Velocity Detection Parameters', 'velocity_detection_parameters.md', RadonVelocityAnalysis.get_detection_schema()),
        ('Diameter Detection Parameters', 'diameter_detection_parameters.md', DiameterAnalysis.get_detection_schema()),
    )

    for title, filename, fields in specs:
        document = _build_document(title, fields, version=version, timestamp=timestamp)
        print(document)
        out_path = _OUTPUT_DIR / filename
        out_path.write_text(document, encoding='utf-8')
        print(f'Wrote {out_path}\n')


if __name__ == '__main__':
    main()
