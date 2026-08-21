"""Launch the GUI with ``python -m macro_recorder``."""

from __future__ import annotations

import sys

from .gui import main

if __name__ == "__main__":
    sys.exit(main())
