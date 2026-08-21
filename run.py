"""Convenience launcher so users can double click / run ``python run.py``.

It simply starts the graphical macro recorder.  For the command line interface
use ``python -m macro_recorder.cli`` instead.
"""

from __future__ import annotations

import sys

from macro_recorder.gui import main

if __name__ == "__main__":
    sys.exit(main())
