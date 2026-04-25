"""
Application state definitions.
"""

from dataclasses import dataclass


@dataclass
class PrimarySelection:
    """Primary selection state."""
    file_id: str | None = None
    channel: int | None = None
    roi_id: str | None = None