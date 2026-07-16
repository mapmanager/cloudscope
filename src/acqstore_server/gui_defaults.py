"""Default NiceGUI widget classes/props for AcqStore Server status UI.

Copied locally (do not import ``nicewidgets`` or ``cloudscope`` from this
package). Must be called before any ``ui.*`` widgets are created.
"""

from __future__ import annotations

from nicegui import ui


def setUpGuiDefaults(text_size: str = 'text-xs') -> None:
    """Set default classes and props for common NiceGUI elements.

    Args:
        text_size: Tailwind text size class (e.g. ``text-xs``).
    """
    text_size_quasar = {
        'text-xs': 'xs',
        'text-sm': 'sm',
        'text-base': 'md',
        'text-lg': 'lg',
    }[text_size]

    ui.label.default_classes(f'{text_size} select-text')
    ui.label.default_props('dense')

    ui.button.default_classes(text_size)
    ui.button.default_props('dense')

    ui.checkbox.default_classes(text_size)
    ui.checkbox.default_props(f'dense size={text_size_quasar}')

    ui.select.default_classes(text_size)
    ui.select.default_props('dense')

    ui.input.default_classes(text_size)
    ui.input.default_props('dense')

    ui.number.default_classes(text_size)
    ui.number.default_props('dense')

    ui.expansion.default_classes(text_size)
    ui.expansion.default_props('dense')

    ui.slider.default_classes(text_size)
    ui.slider.default_props('dense')

    ui.linear_progress.default_classes(text_size)
    ui.linear_progress.default_props('dense')

    ui.menu.default_classes(text_size)
    ui.menu.default_props('dense')

    ui.menu_item.default_classes(text_size)
    ui.menu_item.default_props('dense')

    ui.radio.default_classes(text_size)
    ui.radio.default_props('dense')

    ui.textarea.default_classes(text_size)
    ui.textarea.default_props('dense')
