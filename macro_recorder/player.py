"""Replay a recorded :class:`~macro_recorder.events.Macro`.

Playback runs on a background thread so a GUI stays responsive and can request
a stop at any time.  Timing is reproduced relative to the recording, optionally
scaled by a ``speed`` multiplier.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from pynput import keyboard, mouse

from .events import (
    KeyEvent,
    Macro,
    MacroEvent,
    MouseClickEvent,
    MouseMoveEvent,
    MouseScrollEvent,
)


def string_to_key(value: str):
    """Inverse of :func:`macro_recorder.recorder.key_to_string`."""

    if value.startswith("Key."):
        name = value.split(".", 1)[1]
        try:
            return getattr(keyboard.Key, name)
        except AttributeError:
            # Unknown special key; fall back to typing nothing meaningful.
            return keyboard.KeyCode.from_char(" ")
    if value.startswith("<") and value.endswith(">"):
        # Virtual-key-code only key, e.g. "<65>".
        try:
            return keyboard.KeyCode.from_vk(int(value[1:-1]))
        except ValueError:
            return keyboard.KeyCode.from_char(" ")
    # A regular printable character.
    return keyboard.KeyCode.from_char(value)


def string_to_button(value: str):
    """Inverse of :func:`macro_recorder.recorder.button_to_string`."""

    if value.startswith("Button."):
        name = value.split(".", 1)[1]
        try:
            return getattr(mouse.Button, name)
        except AttributeError:
            return mouse.Button.left
    return mouse.Button.left


class Player:
    """Replay macros using ``pynput`` controllers.

    Parameters
    ----------
    speed:
        Playback speed multiplier.  ``2.0`` plays twice as fast, ``0.5`` half
        speed.  Must be greater than 0.
    on_progress:
        Optional callback ``(index, total)`` invoked before each event.
    on_finish:
        Optional callback invoked once playback completes or is stopped.
    """

    def __init__(
        self,
        speed: float = 1.0,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_finish: Optional[Callable[[], None]] = None,
    ) -> None:
        if speed <= 0:
            raise ValueError("speed must be greater than 0")
        self.speed = speed
        self.on_progress = on_progress
        self.on_finish = on_finish

        self._keyboard = keyboard.Controller()
        self._mouse = mouse.Controller()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ #
    @property
    def is_playing(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def play(self, macro: Macro, repeat: int = 1, blocking: bool = False) -> None:
        """Replay ``macro``.

        Parameters
        ----------
        repeat:
            Number of times to run through the macro.  Use ``0`` for an
            infinite loop (stop with :meth:`stop`).
        blocking:
            When ``True`` this call returns only after playback finishes.
        """

        if self.is_playing:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, args=(macro, repeat), daemon=True
        )
        self._thread.start()

        if blocking:
            self._thread.join()

    def stop(self) -> None:
        """Request that playback stop as soon as possible."""

        self._stop_event.set()

    def wait(self, timeout: Optional[float] = None) -> None:
        """Block until the current playback thread finishes."""

        if self._thread is not None:
            self._thread.join(timeout)

    # ------------------------------------------------------------------ #
    def _run(self, macro: Macro, repeat: int) -> None:
        try:
            iteration = 0
            while not self._stop_event.is_set():
                if repeat != 0 and iteration >= repeat:
                    break
                iteration += 1
                self._play_once(macro)
        finally:
            if self.on_finish is not None:
                try:
                    self.on_finish()
                except Exception:
                    pass

    def _play_once(self, macro: Macro) -> None:
        total = len(macro.events)
        previous_time = 0.0
        for index, event in enumerate(macro.events):
            if self._stop_event.is_set():
                return

            # Reproduce the inter-event delay, scaled by the speed factor.
            delay = (event.time - previous_time) / self.speed
            if delay > 0:
                # Sleep in small slices so a stop request is honored quickly.
                self._interruptible_sleep(delay)
                if self._stop_event.is_set():
                    return
            previous_time = event.time

            if self.on_progress is not None:
                try:
                    self.on_progress(index + 1, total)
                except Exception:
                    pass

            self._dispatch(event)

    def _interruptible_sleep(self, seconds: float) -> None:
        deadline = time.perf_counter() + seconds
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0 or self._stop_event.is_set():
                return
            time.sleep(min(remaining, 0.02))

    # ------------------------------------------------------------------ #
    def _dispatch(self, event: MacroEvent) -> None:
        if isinstance(event, KeyEvent):
            key = string_to_key(event.key)
            if event.pressed:
                self._keyboard.press(key)
            else:
                self._keyboard.release(key)
        elif isinstance(event, MouseMoveEvent):
            self._mouse.position = (event.x, event.y)
        elif isinstance(event, MouseClickEvent):
            self._mouse.position = (event.x, event.y)
            button = string_to_button(event.button)
            if event.pressed:
                self._mouse.press(button)
            else:
                self._mouse.release(button)
        elif isinstance(event, MouseScrollEvent):
            self._mouse.position = (event.x, event.y)
            self._mouse.scroll(event.dx, event.dy)
