"""Keyboard & mouse macro recorder/player for Windows 10 (and other desktops).

This package provides:

* :mod:`macro_recorder.events`   - serializable event model for a macro.
* :mod:`macro_recorder.recorder` - captures keyboard/mouse input into a macro.
* :mod:`macro_recorder.player`   - replays a recorded macro.
* :mod:`macro_recorder.storage`  - loads/saves macros as JSON files.
* :mod:`macro_recorder.hotkeys`  - global hotkey manager built on pynput.
* :mod:`macro_recorder.gui`      - a small Tkinter GUI front-end.
* :mod:`macro_recorder.cli`      - a command line front-end.
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
