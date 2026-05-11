"""Utilities for adding visible handles to NiceGUI splitters."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from nicegui import ui

if TYPE_CHECKING:
    from nicegui.elements.splitter import QSplitter

Orientation = Literal['horizontal', 'vertical']
Offset = Literal['center', 'before', 'after']

_SPLITTER_HANDLE_CSS_ADDED = False


def add_splitter_handle(
    splitter: QSplitter,
    *,
    on_dblclick: Callable[[], None] | None = None,
    orientation: Orientation = 'horizontal',
    offset: Offset = 'center',
) -> None:
    """Add a small visible splitter handle to a NiceGUI splitter separator.

    Args:
        splitter: NiceGUI splitter element whose separator should receive the
            visible handle.
        on_dblclick: Optional callback invoked when the handle is double-clicked.
        orientation: Handle orientation. Use ``'vertical'`` for left/right
            splitters and ``'horizontal'`` for top/bottom splitters.
        offset: Placement bias within the separator. ``'after'`` is useful when
            the ``before`` pane can collapse to a very small size.

    Returns:
        None.
    """
    _ensure_splitter_handle_css()

    wrap_classes = ['cloudscope-splitter-handle-wrap']
    if offset == 'before':
        wrap_classes.append('cloudscope-splitter-handle-wrap-before')
    elif offset == 'after':
        wrap_classes.append('cloudscope-splitter-handle-wrap-after')

    handle_class = 'cloudscope-splitter-handle-vertical' if orientation == 'vertical' else 'cloudscope-splitter-handle'

    with splitter.separator:
        with ui.element('div').classes(' '.join(wrap_classes)):
            handle = ui.element('div').classes(handle_class)
            if on_dblclick is not None:
                handle.on('dblclick', lambda _event: on_dblclick())


def _ensure_splitter_handle_css() -> None:
    """Install splitter-handle CSS once per process.

    Returns:
        None.
    """
    global _SPLITTER_HANDLE_CSS_ADDED
    if _SPLITTER_HANDLE_CSS_ADDED:
        return
    ui.add_css(
        """
        .cloudscope-splitter-handle-wrap {
            height: 100%;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
        }
        .cloudscope-splitter-handle-wrap-before {
            align-items: flex-start;
            justify-content: flex-start;
        }
        .cloudscope-splitter-handle-wrap-after {
            align-items: flex-end;
            justify-content: flex-end;
        }
        .cloudscope-splitter-handle,
        .cloudscope-splitter-handle-vertical {
            border-radius: 4px;
            background: rgba(148, 163, 184, 0.8);
            pointer-events: auto;
        }
        .cloudscope-splitter-handle {
            width: 26px;
            height: 5px;
        }
        .cloudscope-splitter-handle-vertical {
            width: 5px;
            height: 26px;
        }
        """
    )
    _SPLITTER_HANDLE_CSS_ADDED = True
