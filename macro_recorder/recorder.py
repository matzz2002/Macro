"""Capture keyboard and mouse input into a :class:`~macro_recorder.events.Macro`.

The :class:`Recorder` uses ``pynput`` listeners running on background threads.
Movement events are throttled so a recording does not fill up with thousands of
near-identical points.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from pynput import keyboard, mouse

from .events import (
    KeyEvent,
    Macro,
    MouseClickEvent,
    MouseMoveEvent,
    MouseScrollEvent,
)


def key_to_string(key) -> str:
    """Convert a ``pynput`` key object into a portable string.

    Regular characters become themselves (``"a"``); special keys become their
    canonical ``pynput`` name (``"Key.enter"``).
    """

    if isinstance(key, keyboard.KeyCode):
        if key.char is not None:
            return key.char
        # Some keys (e.g. from a numeric keypad) only expose a virtual code.
        return f"<{key.vk}>"
    # ``keyboard.Key`` members stringify as ``"Key.enter"`` etc.
    return str(key)


def button_to_string(button) -> str:
    """Convert a ``pynput`` mouse button into a portable string."""

    return str(button)


class Recorder:
    """Record keyboard and mouse activity.

    Parameters
    ----------
    capture_mouse_move:
        When ``True`` (default) absolute cursor movements are recorded.
    move_min_interval:
        Minimum number of seconds between two recorded move events.  This
        throttles the otherwise very high frequency of movement callbacks.
    on_event:
        Optional callback invoked (from a listener thread) after every event is
        appended.  Useful for live UI updates.
    """

    def __init__(
        self,
        capture_mouse_move: bool = True,
        move_min_interval: float = 0.02,
        on_event: Optional[Callable[[object], None]] = None,
    ) -> None:
        self.capture_mouse_move = capture_mouse_move
        self.move_min_interval = move_min_interval
        self.on_event = on_event

        self._macro = Macro()
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        self._start_time: float = 0.0
        self._last_move_time: float = 0.0
        self._recording = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, name: str = "Recorded macro") -> None:
        """Begin recording.  Any previously captured events are discarded."""

        if self._recording:
            return

        self._macro = Macro(name=name)
        self._start_time = time.perf_counter()
        self._last_move_time = 0.0
        self._recording = True

        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._keyboard_listener.start()
        self._mouse_listener.start()

    def stop(self) -> Macro:
        """Stop recording and return the captured macro."""

        if not self._recording:
            return self._macro

        self._recording = False
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener = None
        return self._macro

    @property
    def macro(self) -> Macro:
        return self._macro

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _elapsed(self) -> float:
        return time.perf_counter() - self._start_time

    def _append(self, event) -> None:
        if not self._recording:
            return
        with self._lock:
            self._macro.add(event)
        if self.on_event is not None:
            try:
                self.on_event(event)
            except Exception:
                # Never let a UI callback break recording.
                pass

    # -- keyboard callbacks -------------------------------------------- #
    def _on_press(self, key) -> None:
        self._append(KeyEvent(time=self._elapsed(), key=key_to_string(key), pressed=True))

    def _on_release(self, key) -> None:
        self._append(KeyEvent(time=self._elapsed(), key=key_to_string(key), pressed=False))

    # -- mouse callbacks ----------------------------------------------- #
    def _on_move(self, x, y) -> None:
        if not self.capture_mouse_move:
            return
        now = time.perf_counter()
        if now - self._last_move_time < self.move_min_interval:
            return
        self._last_move_time = now
        self._append(MouseMoveEvent(time=self._elapsed(), x=int(x), y=int(y)))

    def _on_click(self, x, y, button, pressed) -> None:
        self._append(
            MouseClickEvent(
                time=self._elapsed(),
                x=int(x),
                y=int(y),
                button=button_to_string(button),
                pressed=bool(pressed),
            )
        )

    def _on_scroll(self, x, y, dx, dy) -> None:
        self._append(
            MouseScrollEvent(
                time=self._elapsed(),
                x=int(x),
                y=int(y),
                dx=int(dx),
                dy=int(dy),
            )
        )
