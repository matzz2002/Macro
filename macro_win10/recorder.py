"""Keyboard and mouse recording built on pynput."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from .models import Macro, MacroEvent

RecordedEventCallback = Callable[[MacroEvent], None]


def _require_pynput() -> tuple[Any, Any]:
    try:
        from pynput import keyboard, mouse
    except ImportError as exc:
        raise RuntimeError(
            "Recording requires pynput. Install dependencies with "
            "`python -m pip install -r requirements.txt`."
        ) from exc
    return keyboard, mouse


def normalize_key(key: Any) -> str:
    """Convert a pynput key into a pyautogui-friendly key name."""

    char = getattr(key, "char", None)
    if char:
        return char

    name = getattr(key, "name", None)
    if name:
        return str(name)

    # pynput falls back to strings like "'a'" for printable keys.
    key_text = str(key)
    if len(key_text) >= 2 and key_text[0] == key_text[-1] == "'":
        return key_text[1:-1]
    return key_text


class RecorderSession:
    """Record global keyboard and mouse input until stopped."""

    def __init__(
        self,
        *,
        name: str = "Recorded Macro",
        stop_key: str = "f8",
        on_event: RecordedEventCallback | None = None,
        mouse_move_interval: float = 0.01,
    ) -> None:
        self.name = name
        self.stop_key = stop_key.lower()
        self.on_event = on_event
        self.mouse_move_interval = mouse_move_interval
        self._events: list[MacroEvent] = []
        self._lock = threading.Lock()
        self._started_at = 0.0
        self._last_mouse_move = 0.0
        self._keyboard_listener: Any | None = None
        self._mouse_listener: Any | None = None
        self._recording = threading.Event()

    @property
    def is_recording(self) -> bool:
        return self._recording.is_set()

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def start(self) -> None:
        if self.is_recording:
            raise RuntimeError("recording is already running")

        keyboard, mouse = _require_pynput()
        self._events = []
        self._started_at = time.perf_counter()
        self._last_mouse_move = 0.0
        self._recording.set()

        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_down,
            on_release=self._on_key_up,
        )
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
        )
        self._keyboard_listener.start()
        self._mouse_listener.start()

    def stop(self) -> Macro:
        if not self.is_recording:
            return self.macro()

        self._recording.clear()
        self._stop_listener(self._keyboard_listener)
        self._stop_listener(self._mouse_listener)
        return self.macro()

    def macro(self) -> Macro:
        with self._lock:
            events = list(self._events)
        return Macro(name=self.name, events=events)

    def _event_time(self) -> float:
        return time.perf_counter() - self._started_at

    def _add_event(self, event_type: str, data: dict[str, Any]) -> None:
        if not self.is_recording:
            return

        event = MacroEvent(time=self._event_time(), type=event_type, data=data)
        with self._lock:
            self._events.append(event)

        if self.on_event:
            self.on_event(event)

    def _on_key_down(self, key: Any) -> bool | None:
        key_name = normalize_key(key)
        if key_name.lower() == self.stop_key:
            self.stop()
            return False
        self._add_event("key_down", {"key": key_name})
        return None

    def _on_key_up(self, key: Any) -> bool | None:
        key_name = normalize_key(key)
        if key_name.lower() != self.stop_key:
            self._add_event("key_up", {"key": key_name})
        return None

    def _on_mouse_move(self, x: int, y: int) -> None:
        now = self._event_time()
        if now - self._last_mouse_move < self.mouse_move_interval:
            return
        self._last_mouse_move = now
        self._add_event("mouse_move", {"x": x, "y": y})

    def _on_mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        event_type = "mouse_down" if pressed else "mouse_up"
        button_name = getattr(button, "name", str(button))
        self._add_event(event_type, {"x": x, "y": y, "button": button_name})

    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        self._add_event("mouse_scroll", {"x": x, "y": y, "dx": dx, "dy": dy})

    @staticmethod
    def _stop_listener(listener: Any | None) -> None:
        if listener is None:
            return
        try:
            listener.stop()
        except RuntimeError:
            pass
