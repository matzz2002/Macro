"""Record keyboard and mouse activity into a :class:`~macro_recorder.events.Macro`."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Callable, List, Optional

from pynput import keyboard, mouse

from . import __version__
from .events import (
    KEY_PRESS,
    KEY_RELEASE,
    MOUSE_CLICK,
    MOUSE_MOVE,
    MOUSE_SCROLL,
    Event,
    Macro,
)
from .keyutils import button_to_str, key_to_str

# Callback invoked every time a new event is captured (used by the GUI to keep a
# live counter up to date).  It receives the total number of events so far.
ProgressCallback = Callable[[int], None]


class MacroRecorder:
    """Capture input events until :meth:`stop` is called.

    The recorder installs :mod:`pynput` listeners which run on their own
    background threads, so recording never blocks the caller.  Mouse movement is
    optional (it can create very large recordings) and can be throttled with
    ``mouse_move_interval`` so at most one move event is stored per interval.
    """

    def __init__(
        self,
        capture_mouse_move: bool = True,
        mouse_move_interval: float = 0.02,
        on_event: Optional[ProgressCallback] = None,
    ) -> None:
        self.capture_mouse_move = capture_mouse_move
        self.mouse_move_interval = max(0.0, mouse_move_interval)
        self.on_event = on_event

        self._events: List[Event] = []
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._last_move_time: float = 0.0
        self._recording = False

        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None

    # ------------------------------------------------------------------ state
    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    # ------------------------------------------------------------- public API
    def start(self) -> None:
        """Begin recording.  Raises :class:`RuntimeError` if already running."""

        if self._recording:
            raise RuntimeError("Recorder is already running")

        self._events = []
        self._start_time = time.perf_counter()
        self._last_move_time = 0.0
        self._recording = True

        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move if self.capture_mouse_move else None,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._keyboard_listener.start()
        self._mouse_listener.start()

    def stop(self) -> Macro:
        """Stop recording and return the captured :class:`Macro`."""

        if not self._recording:
            raise RuntimeError("Recorder is not running")

        self._recording = False
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener = None

        with self._lock:
            events = list(self._events)

        return Macro(
            name=f"Macro {datetime.now():%Y-%m-%d %H:%M:%S}",
            events=events,
            created_at=datetime.now().isoformat(timespec="seconds"),
            captured_mouse_move=self.capture_mouse_move,
            app_version=__version__,
        )

    # ------------------------------------------------------------- internals
    def _elapsed(self) -> float:
        return time.perf_counter() - self._start_time

    def _append(self, event: Event) -> None:
        with self._lock:
            self._events.append(event)
            count = len(self._events)
        if self.on_event is not None:
            # Never let a misbehaving callback break the listener thread.
            try:
                self.on_event(count)
            except Exception:  # pragma: no cover - defensive
                pass

    # -- keyboard callbacks
    def _on_press(self, key) -> None:
        self._append(Event(kind=KEY_PRESS, time=self._elapsed(), key=key_to_str(key)))

    def _on_release(self, key) -> None:
        self._append(
            Event(kind=KEY_RELEASE, time=self._elapsed(), key=key_to_str(key))
        )

    # -- mouse callbacks
    def _on_move(self, x: int, y: int) -> None:
        now = time.perf_counter()
        if self.mouse_move_interval and (
            now - self._last_move_time < self.mouse_move_interval
        ):
            return
        self._last_move_time = now
        self._append(Event(kind=MOUSE_MOVE, time=self._elapsed(), x=int(x), y=int(y)))

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        self._append(
            Event(
                kind=MOUSE_CLICK,
                time=self._elapsed(),
                x=int(x),
                y=int(y),
                button=button_to_str(button),
                pressed=bool(pressed),
            )
        )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        self._append(
            Event(
                kind=MOUSE_SCROLL,
                time=self._elapsed(),
                x=int(x),
                y=int(y),
                dx=int(dx),
                dy=int(dy),
            )
        )
