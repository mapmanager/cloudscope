"""Static checks for event-analysis table widget configuration."""

from __future__ import annotations

from pathlib import Path


def test_event_analysis_view_uses_compact_filtered_resizing_table_config() -> None:
    """EventAnalysisView should use compact, non-filtering, resize-aware table config."""
    source_path = Path(__file__).parents[2] / 'src/cloudscope/views/event_analysis_view.py'
    source = source_path.read_text()

    assert 'scaled_row_header_heights_px' in source
    assert 'cell_font_size_px=font_px' in source
    assert 'row_height=row_h' in source
    assert 'header_height=header_h' in source
    assert 'fit_columns_on_grid_resize=True' in source
    assert '"filter": False' in source
