"""Convenience launcher for the GUI (also used as the PyInstaller entry point).

Double-click this file (or run ``python run_gui.py``) to open the macro
recorder window.
"""

from macro_recorder.gui import run

if __name__ == "__main__":
    raise SystemExit(run())
