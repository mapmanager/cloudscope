"""CLI entry: ``python -m acqstore_server``.

Default: API-only uvicorn (no native window).

Native status UI (for packing / local try)::

    ACQSTORE_SERVER_NATIVE=1 uv run python -m acqstore_server

Or::

    uv run python -m acqstore_server.desktop

Packaging rules (NiceGUI native / PyInstaller):
    - ``multiprocessing.freeze_support()`` under ``__main__`` only.
    - Never call ``main()`` from ``__mp_main__``.
"""

from __future__ import annotations

import multiprocessing

from acqstore_server.app import main


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
