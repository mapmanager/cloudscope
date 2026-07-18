"""Desktop entry for nicegui-pack / double-click (native status UI).

Sets ``ACQSTORE_SERVER_NATIVE=1`` then runs the shared ``main()``.

Packaging (PyInstaller / nicegui-pack):
    - ``multiprocessing.freeze_support()`` under ``__main__`` only.
    - Never call ``main()`` from ``__mp_main__``.
    - NiceGUI ``reload=False`` (enforced in ``main_native``).
"""

from __future__ import annotations

import multiprocessing
import os

os.environ.setdefault('ACQSTORE_SERVER_NATIVE', '1')

from acqstore_server.app import main  # noqa: E402


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
