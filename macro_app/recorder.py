from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .models import ActionType, MacroAction


ActionCallback = Callable[[MacroAction], None]
StatusCallback = Callable[[str], None]


class RecorderError(RuntimeError):
    pass


def _load_pynput():
    try:
        from pynput import keyboard, mouse

        return keyboard, mouse
    except Exception as exc:
        raise RecorderError(
            "Brakuje zależności pynput lub backendu wejścia. Zainstaluj wymagania i uruchom aplikację na Windows."
        ) from exc


class MacroRecorder:
    def __init__(self, action_callback: ActionCallback | None = None, status_callback: StatusCallback | None = None) -> None:
        self.action_callback = action_callback
        self.status_callback = status_callback
        self.actions: list[MacroAction] = []
        self.record_mouse_moves = False
        self.mouse_move_interval_ms = 35
        self._lock = threading.Lock()
        self._last_event = 0.0
        self._last_mouse_move = 0.0
        self._keyboard_listener = None
        self._mouse_listener = None
        self._recording = False

    def start(self, record_mouse_moves: bool = False, mouse_move_interval_ms: int = 35) -> None:
        if self._recording:
            return
        keyboard, mouse = _load_pynput()
        self.actions = []
        self.record_mouse_moves = record_mouse_moves
        self.mouse_move_interval_ms = max(10, mouse_move_interval_ms)
        self._last_event = time.monotonic()
        self._last_mouse_move = 0.0
        self._recording = True
        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_down, on_release=self._on_key_up, suppress=False)
        self._mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_move=self._on_move if self.record_mouse_moves else None,
            suppress=False,
        )
        self._keyboard_listener.start()
        self._mouse_listener.start()
        self._notify("Nagrywanie")

    def stop(self) -> list[MacroAction]:
        if not self._recording:
            return list(self.actions)
        self._recording = False
        for listener in (self._keyboard_listener, self._mouse_listener):
            if listener is not None:
                listener.stop()
        self._keyboard_listener = None
        self._mouse_listener = None
        self._notify("Makro zatrzymane")
        return list(self.actions)

    def is_recording(self) -> bool:
        return self._recording

    def _on_key_down(self, key) -> None:
        self._append_event(MacroAction(ActionType.KEY_DOWN, {"key": key_to_text(key)}))

    def _on_key_up(self, key) -> None:
        self._append_event(MacroAction(ActionType.KEY_UP, {"key": key_to_text(key)}))

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        if pressed:
            self._append_event(
                MacroAction(
                    ActionType.MOUSE_CLICK,
                    {"button": mouse_button_to_text(button), "x": int(x), "y": int(y), "clicks": 1},
                )
            )

    def _on_move(self, x: int, y: int) -> None:
        now = time.monotonic()
        if (now - self._last_mouse_move) * 1000 < self.mouse_move_interval_ms:
            return
        self._last_mouse_move = now
        self._append_event(MacroAction(ActionType.MOUSE_MOVE, {"x": int(x), "y": int(y), "duration_ms": 0}))

    def _append_event(self, action: MacroAction) -> None:
        if not self._recording:
            return
        with self._lock:
            now = time.monotonic()
            delay_ms = max(0, round((now - self._last_event) * 1000))
            self._last_event = now
            if delay_ms:
                self._append_action_locked(MacroAction(ActionType.DELAY, {"ms": delay_ms}))
            self._append_action_locked(action)

    def _append_action_locked(self, action: MacroAction) -> None:
        self.actions.append(action)
        if self.action_callback:
            self.action_callback(action)

    def _notify(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)


def key_to_text(key) -> str:
    char = getattr(key, "char", None)
    if char:
        return char
    name = getattr(key, "name", None)
    if name:
        return name.replace("_l", "").replace("_r", "").replace("_", "")
    text = str(key)
    if text.startswith("Key."):
        return text[4:].replace("_", "")
    return text.strip("'")


def mouse_button_to_text(button) -> str:
    name = getattr(button, "name", "")
    return {"left": "left", "right": "right", "middle": "middle", "x1": "x1", "x2": "x2"}.get(name, name or "left")
