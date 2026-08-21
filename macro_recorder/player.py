"""Replay a recorded :class:`~macro_recorder.events.Macro`."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from pynput import keyboard, mouse

from .events import (
    KEY_PRESS,
    KEY_RELEASE,
    MOUSE_CLICK,
    MOUSE_MOVE,
    MOUSE_SCROLL,
    Event,
    Macro,
)
from .keyutils import str_to_button, str_to_key

# Called with the index of the event about to be played and the total count.
ProgressCallback = Callable[[int, int], None]
# Called when playback finishes (either naturally or because it was stopped).
DoneCallback = Callable[[], None]


class MacroPlayer:
    """Play a macro back, optionally faster/slower and repeated.

    Playback happens on a background thread so a GUI stays responsive.  Call
    :meth:`stop` to abort; the player checks the stop flag while it sleeps
    between events so it reacts promptly.
    """

    def __init__(self) -> None:
        self._keyboard = keyboard.Controller()
        self._mouse = mouse.Controller()

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._playing = False

    @property
    def is_playing(self) -> bool:
        return self._playing

    # ------------------------------------------------------------- public API
    def play(
        self,
        macro: Macro,
        speed: float = 1.0,
        repeat: int = 1,
        on_progress: Optional[ProgressCallback] = None,
        on_done: Optional[DoneCallback] = None,
        block: bool = False,
    ) -> None:
        """Start playing ``macro``.

        ``repeat`` values of ``0`` (or below) loop forever until :meth:`stop`.
        When ``block`` is ``True`` the call runs synchronously on the current
        thread instead of spawning a worker.
        """

        if self._playing:
            raise RuntimeError("Player is already running")
        if speed <= 0:
            raise ValueError("speed must be greater than 0")

        self._stop_event.clear()
        self._playing = True

        args = (macro, speed, repeat, on_progress, on_done)
        if block:
            self._run(*args)
        else:
            self._thread = threading.Thread(
                target=self._run, args=args, daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        """Request playback to stop as soon as possible."""

        self._stop_event.set()

    def wait(self, timeout: Optional[float] = None) -> None:
        """Block until the background playback thread finishes."""

        if self._thread is not None:
            self._thread.join(timeout)

    # ------------------------------------------------------------- internals
    def _run(
        self,
        macro: Macro,
        speed: float,
        repeat: int,
        on_progress: Optional[ProgressCallback],
        on_done: Optional[DoneCallback],
    ) -> None:
        try:
            total = len(macro.events)
            loop = 0
            while not self._stop_event.is_set():
                start = time.perf_counter()
                for index, event in enumerate(macro.events):
                    if self._stop_event.is_set():
                        break
                    target = start + (event.time / speed)
                    self._sleep_until(target)
                    if self._stop_event.is_set():
                        break
                    if on_progress is not None:
                        try:
                            on_progress(index + 1, total)
                        except Exception:  # pragma: no cover - defensive
                            pass
                    self._dispatch(event)

                loop += 1
                if repeat > 0 and loop >= repeat:
                    break
        finally:
            self._playing = False
            if on_done is not None:
                try:
                    on_done()
                except Exception:  # pragma: no cover - defensive
                    pass

    def _sleep_until(self, target: float) -> None:
        """Sleep until ``target`` (perf_counter time), waking early to stop."""

        while not self._stop_event.is_set():
            remaining = target - time.perf_counter()
            if remaining <= 0:
                return
            # Wake up frequently so stop() feels responsive even on long waits.
            self._stop_event.wait(min(remaining, 0.05))

    def _dispatch(self, event: Event) -> None:
        kind = event.kind
        if kind == KEY_PRESS:
            self._keyboard.press(str_to_key(event.key))
        elif kind == KEY_RELEASE:
            self._keyboard.release(str_to_key(event.key))
        elif kind == MOUSE_MOVE:
            self._mouse.position = (event.x, event.y)
        elif kind == MOUSE_CLICK:
            self._mouse.position = (event.x, event.y)
            button = str_to_button(event.button)
            if event.pressed:
                self._mouse.press(button)
            else:
                self._mouse.release(button)
        elif kind == MOUSE_SCROLL:
            self._mouse.position = (event.x, event.y)
            self._mouse.scroll(event.dx or 0, event.dy or 0)
