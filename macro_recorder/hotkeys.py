"""Global hotkey management built on ``pynput.keyboard.GlobalHotKeys``.

A :class:`HotkeyManager` lets the GUI (or CLI) bind system-wide shortcuts such
as ``F9`` to start/stop recording even when the application window is not
focused.  Hotkeys use the ``pynput`` syntax, e.g. ``"<f9>"`` or ``"<ctrl>+<f10>"``.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from pynput import keyboard


class HotkeyManager:
    """Register and run global hotkeys on a background thread."""

    def __init__(self) -> None:
        self._bindings: Dict[str, Callable[[], None]] = {}
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def register(self, combination: str, callback: Callable[[], None]) -> None:
        """Bind ``combination`` (pynput syntax) to ``callback``.

        Changes only take effect the next time :meth:`start` is called, so
        register all hotkeys before starting.
        """

        self._bindings[combination] = callback

    def clear(self) -> None:
        self._bindings.clear()

    @property
    def is_running(self) -> bool:
        return self._listener is not None and self._listener.running

    def start(self) -> None:
        """Start listening for the registered hotkeys."""

        if self.is_running or not self._bindings:
            return
        self._listener = keyboard.GlobalHotKeys(dict(self._bindings))
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for hotkeys."""

        if self._listener is not None:
            self._listener.stop()
            self._listener = None
