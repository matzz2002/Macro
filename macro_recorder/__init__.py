"""A keyboard and mouse macro recorder/player for Windows 10.

The package exposes the high level building blocks so it can be used both as a
library and through the bundled GUI (``python -m macro_recorder``) or CLI
(``python -m macro_recorder.cli``).

The recorder/player/GUI pieces depend on :mod:`pynput`; they are imported lazily
so the pure data layer (:mod:`macro_recorder.events` and
:mod:`macro_recorder.storage`) can be used even where ``pynput`` is unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .events import Event, Macro
from .storage import load_macro, save_macro

__all__ = [
    "Event",
    "Macro",
    "MacroRecorder",
    "MacroPlayer",
    "load_macro",
    "save_macro",
    "__version__",
]

__version__ = "1.0.0"

# Map of lazily imported attributes -> the submodule that provides them.  These
# pull in ``pynput`` only when actually accessed.
_LAZY = {
    "MacroRecorder": "recorder",
    "MacroPlayer": "player",
}

if TYPE_CHECKING:  # pragma: no cover - for type checkers/IDEs only
    from .player import MacroPlayer
    from .recorder import MacroRecorder


def __getattr__(name: str) -> Any:  # PEP 562 module level attribute access
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    module = import_module(f".{module_name}", __name__)
    return getattr(module, name)
