from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable

from .models import ActionType, Macro, MacroAction, RunMode


StatusCallback = Callable[[str], None]


class PlaybackError(RuntimeError):
    pass


def _load_pynput():
    try:
        from pynput import keyboard, mouse

        return keyboard, mouse
    except Exception as exc:
        raise PlaybackError(
            "Brakuje zależności pynput lub backendu wejścia. Zainstaluj wymagania i uruchom aplikację na Windows."
        ) from exc


class MacroRunner(threading.Thread):
    def __init__(self, macro: Macro, stop_event: threading.Event, status_callback: StatusCallback | None = None) -> None:
        super().__init__(daemon=True)
        self.macro = macro
        self.stop_event = stop_event
        self.status_callback = status_callback
        keyboard, mouse = _load_pynput()
        self.keyboard_module = keyboard
        self.mouse_module = mouse
        self.keyboard = keyboard.Controller()
        self.mouse = mouse.Controller()

    def run(self) -> None:
        try:
            self._notify(f"Makro aktywne: {self.macro.name}")
            repeats = self._repeat_iterator()
            for _ in repeats:
                if self.stop_event.is_set():
                    break
                self._play_actions(self.macro.actions)
        except Exception as exc:
            self._notify(f"Błąd makra '{self.macro.name}': {exc}")
        finally:
            self._release_safety_keys()
            self._notify(f"Makro zatrzymane: {self.macro.name}")

    def _repeat_iterator(self):
        if self.macro.run_mode == RunMode.REPEAT_COUNT:
            return range(max(1, self.macro.repeat_count))
        if self.macro.run_mode in {RunMode.TOGGLE, RunMode.HOLD}:
            return iter(int, 1)
        return range(1)

    def _play_actions(self, actions: list[MacroAction]) -> None:
        for action in actions:
            if self.stop_event.is_set():
                return
            self._play_action(action)

    def _play_action(self, action: MacroAction) -> None:
        params = action.params
        action_type = action.type
        if action_type == ActionType.DELAY:
            self._sleep_delay(params)
        elif action_type == ActionType.KEY_DOWN:
            self.keyboard.press(self._key(params.get("key", "")))
        elif action_type == ActionType.KEY_UP:
            self.keyboard.release(self._key(params.get("key", "")))
        elif action_type == ActionType.KEY_PRESS:
            self._press_key(str(params.get("key", "")))
        elif action_type == ActionType.HOTKEY:
            self._hotkey([str(key) for key in params.get("keys", [])])
        elif action_type == ActionType.MOUSE_CLICK:
            self._mouse_click(params)
        elif action_type == ActionType.MOUSE_MOVE:
            self._mouse_move(params)
        elif action_type == ActionType.LOOP:
            count = max(1, int(params.get("count", 1)))
            nested = [MacroAction.from_dict(item) for item in params.get("actions", []) if isinstance(item, dict)]
            for _ in range(count):
                if self.stop_event.is_set():
                    return
                self._play_actions(nested)

    def _sleep_delay(self, params: dict) -> None:
        ms = int(params.get("ms", 0))
        random_min = params.get("random_min_ms")
        random_max = params.get("random_max_ms")
        if isinstance(random_min, int) and isinstance(random_max, int) and random_max >= random_min:
            ms = random.randint(random_min, random_max)

        deadline = time.monotonic() + max(0, ms) / 1000
        while not self.stop_event.is_set() and time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(0.02, remaining))

    def _key(self, value: str):
        value = value.strip()
        lower = value.lower()
        key = self.keyboard_module.Key
        aliases = {
            "ctrl": key.ctrl,
            "control": key.ctrl,
            "shift": key.shift,
            "alt": key.alt,
            "win": key.cmd,
            "cmd": key.cmd,
            "enter": key.enter,
            "return": key.enter,
            "esc": key.esc,
            "escape": key.esc,
            "space": key.space,
            "tab": key.tab,
            "backspace": key.backspace,
            "delete": key.delete,
            "insert": key.insert,
            "home": key.home,
            "end": key.end,
            "pageup": key.page_up,
            "pagedown": key.page_down,
            "up": key.up,
            "down": key.down,
            "left": key.left,
            "right": key.right,
            "capslock": key.caps_lock,
        }
        if lower in aliases:
            return aliases[lower]
        if lower.startswith("f") and lower[1:].isdigit():
            function_key = f"f{int(lower[1:])}"
            if hasattr(key, function_key):
                return getattr(key, function_key)
        if len(value) == 1:
            return value
        return value

    def _press_key(self, value: str) -> None:
        key = self._key(value)
        self.keyboard.press(key)
        self.keyboard.release(key)

    def _hotkey(self, keys: list[str]) -> None:
        parsed = [self._key(key) for key in keys]
        for key in parsed:
            if self.stop_event.is_set():
                return
            self.keyboard.press(key)
            time.sleep(0.02)
        for key in reversed(parsed):
            self.keyboard.release(key)
            time.sleep(0.02)

    def _mouse_button(self, value: str):
        button = self.mouse_module.Button
        return {
            "left": button.left,
            "right": button.right,
            "middle": button.middle,
            "x1": getattr(button, "x1", button.middle),
            "x2": getattr(button, "x2", button.middle),
        }.get(value, button.left)

    def _mouse_click(self, params: dict) -> None:
        if isinstance(params.get("x"), int) and isinstance(params.get("y"), int):
            self.mouse.position = (params["x"], params["y"])
        clicks = max(1, int(params.get("clicks", 1)))
        self.mouse.click(self._mouse_button(str(params.get("button", "left"))), clicks)

    def _mouse_move(self, params: dict) -> None:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        duration_ms = max(0, int(params.get("duration_ms", 0)))
        if duration_ms <= 0:
            self.mouse.position = (x, y)
            return

        start_x, start_y = self.mouse.position
        steps = max(1, duration_ms // 10)
        for step in range(1, steps + 1):
            if self.stop_event.is_set():
                return
            fraction = step / steps
            self.mouse.position = (
                round(start_x + (x - start_x) * fraction),
                round(start_y + (y - start_y) * fraction),
            )
            time.sleep(duration_ms / steps / 1000)

    def _release_safety_keys(self) -> None:
        for key_name in ("ctrl", "shift", "alt", "win"):
            try:
                self.keyboard.release(self._key(key_name))
            except Exception:
                pass

    def _notify(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)


class MacroPlayer:
    def __init__(self, status_callback: StatusCallback | None = None) -> None:
        self.status_callback = status_callback
        self._runners: dict[str, tuple[threading.Event, MacroRunner]] = {}
        self._lock = threading.Lock()

    def play(self, macro: Macro) -> None:
        existing: tuple[threading.Event, MacroRunner] | None = None
        with self._lock:
            if macro.id in self._runners:
                if macro.run_mode == RunMode.HOLD:
                    return
                existing = self._runners.pop(macro.id)

            if existing and macro.run_mode == RunMode.TOGGLE:
                existing[0].set()
                return
            if existing:
                existing[0].set()

            stop_event = threading.Event()
            runner = MacroRunner(macro, stop_event, self.status_callback)
            self._runners[macro.id] = (stop_event, runner)
            runner.start()

    def stop(self, macro_id: str) -> None:
        with self._lock:
            item = self._runners.pop(macro_id, None)
        if item:
            item[0].set()

    def stop_all(self) -> None:
        with self._lock:
            items = list(self._runners.values())
            self._runners.clear()
        for stop_event, _runner in items:
            stop_event.set()
        if self.status_callback:
            self.status_callback("Brak aktywnego makra")

    def cleanup_finished(self) -> None:
        with self._lock:
            finished = [macro_id for macro_id, (_event, runner) in self._runners.items() if not runner.is_alive()]
            for macro_id in finished:
                self._runners.pop(macro_id, None)

    def is_running(self) -> bool:
        self.cleanup_finished()
        with self._lock:
            return bool(self._runners)
