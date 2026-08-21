from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from .models import Macro, RunMode
from .validation import Hotkey, ValidationError


HotkeyCallback = Callable[[Macro], None]
ReleaseCallback = Callable[[Macro], None]
PanicCallback = Callable[[], None]
StatusCallback = Callable[[str], None]


class HotkeyError(RuntimeError):
    pass


def _load_pynput():
    try:
        from pynput import keyboard, mouse

        return keyboard, mouse
    except Exception as exc:
        raise HotkeyError(
            "Brakuje zależności pynput lub backendu wejścia. Zainstaluj wymagania i uruchom aplikację na Windows."
        ) from exc


@dataclass
class RegisteredHotkey:
    macro: Macro
    tokens: frozenset[str]


class GlobalHotkeyManager:
    def __init__(
        self,
        on_trigger: HotkeyCallback,
        on_release: ReleaseCallback,
        on_panic: PanicCallback,
        on_status: StatusCallback | None = None,
    ) -> None:
        self.on_trigger = on_trigger
        self.on_release = on_release
        self.on_panic = on_panic
        self.on_status = on_status
        self.panic_tokens = Hotkey.parse("F12").key()
        self._hotkeys: list[RegisteredHotkey] = []
        self._pressed: set[str] = set()
        self._triggered: dict[frozenset[str], Macro] = {}
        self._lock = threading.RLock()
        self._keyboard_listener = None
        self._mouse_listener = None
        self._keyboard_module = None
        self._mouse_module = None

    def set_panic_hotkey(self, value: str) -> None:
        self.panic_tokens = Hotkey.parse(value).key()

    def register_macros(self, macros: list[Macro]) -> list[str]:
        errors: list[str] = []
        registered: list[RegisteredHotkey] = []
        seen: dict[frozenset[str], str] = {self.panic_tokens: "Panic key"}

        for macro in macros:
            if not macro.hotkey.strip():
                continue
            try:
                tokens = Hotkey.parse(macro.hotkey).key()
            except ValidationError as exc:
                errors.append(f"{macro.name}: {exc}")
                continue
            if tokens in seen:
                errors.append(f"{macro.name}: konflikt ze skrótem '{seen[tokens]}'.")
                continue
            seen[tokens] = macro.name
            registered.append(RegisteredHotkey(macro=macro, tokens=tokens))

        with self._lock:
            self._hotkeys = registered
            self._triggered.clear()
        return errors

    def start(self) -> None:
        if self._keyboard_listener is not None:
            return
        keyboard, mouse = _load_pynput()
        self._keyboard_module = keyboard
        self._mouse_module = mouse
        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_down, on_release=self._on_key_up, suppress=False)
        self._mouse_listener = mouse.Listener(on_click=self._on_mouse_click, suppress=False)
        self._keyboard_listener.start()
        self._mouse_listener.start()
        self._notify("Globalne skróty aktywne")

    def stop(self) -> None:
        for listener in (self._keyboard_listener, self._mouse_listener):
            if listener is not None:
                listener.stop()
        self._keyboard_listener = None
        self._mouse_listener = None
        with self._lock:
            self._pressed.clear()
            self._triggered.clear()
        self._notify("Globalne skróty zatrzymane")

    def _on_key_down(self, key) -> None:
        token = self._key_to_token(key)
        if token:
            self._press(token)

    def _on_key_up(self, key) -> None:
        token = self._key_to_token(key)
        if token:
            self._release(token)

    def _on_mouse_click(self, _x: int, _y: int, button, pressed: bool) -> None:
        token = self._mouse_button_to_token(button)
        if not token:
            return
        if pressed:
            self._press(token)
        else:
            self._release(token)

    def _press(self, token: str) -> None:
        callbacks: list[Macro] = []
        panic = False
        with self._lock:
            self._pressed.add(token)
            pressed = frozenset(self._pressed)
            if self.panic_tokens and self.panic_tokens.issubset(pressed) and self.panic_tokens not in self._triggered:
                self._triggered[self.panic_tokens] = Macro(name="Panic")
                panic = True
            for item in self._hotkeys:
                if item.tokens.issubset(pressed) and item.tokens not in self._triggered:
                    self._triggered[item.tokens] = item.macro
                    callbacks.append(item.macro)

        if panic:
            self.on_panic()
        for macro in callbacks:
            self.on_trigger(macro)

    def _release(self, token: str) -> None:
        releases: list[Macro] = []
        with self._lock:
            self._pressed.discard(token)
            pressed = frozenset(self._pressed)
            completed = [tokens for tokens in self._triggered if not tokens.issubset(pressed)]
            for tokens in completed:
                macro = self._triggered.pop(tokens)
                if macro.name == "Panic":
                    continue
                if macro.run_mode == RunMode.HOLD or macro.stop_on_hotkey_release:
                    releases.append(macro)

        for macro in releases:
            self.on_release(macro)

    def _key_to_token(self, key) -> str:
        key_module = self._keyboard_module
        if key_module is None:
            return ""
        special = {
            key_module.Key.ctrl: "ctrl",
            key_module.Key.ctrl_l: "ctrl",
            key_module.Key.ctrl_r: "ctrl",
            key_module.Key.shift: "shift",
            key_module.Key.shift_l: "shift",
            key_module.Key.shift_r: "shift",
            key_module.Key.alt: "alt",
            key_module.Key.alt_l: "alt",
            key_module.Key.alt_r: "alt",
            key_module.Key.cmd: "win",
            key_module.Key.cmd_l: "win",
            key_module.Key.cmd_r: "win",
            key_module.Key.esc: "esc",
            key_module.Key.enter: "enter",
            key_module.Key.space: "space",
            key_module.Key.tab: "tab",
            key_module.Key.backspace: "backspace",
            key_module.Key.delete: "delete",
            key_module.Key.insert: "insert",
            key_module.Key.home: "home",
            key_module.Key.end: "end",
            key_module.Key.page_up: "pageup",
            key_module.Key.page_down: "pagedown",
            key_module.Key.up: "up",
            key_module.Key.down: "down",
            key_module.Key.left: "left",
            key_module.Key.right: "right",
        }
        if key in special:
            return special[key]
        name = getattr(key, "name", "")
        if name and name.startswith("f") and name[1:].isdigit():
            return name
        char = getattr(key, "char", None)
        if char:
            return char.lower()
        return ""

    def _mouse_button_to_token(self, button) -> str:
        name = getattr(button, "name", "")
        return {"left": "mouse_left", "right": "mouse_right", "middle": "mouse_middle", "x1": "mouse4", "x2": "mouse5"}.get(name, "")

    def _notify(self, message: str) -> None:
        if self.on_status:
            self.on_status(message)
