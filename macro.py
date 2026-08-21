#!/usr/bin/env python3
"""Windows 10 keyboard and mouse macro player.

Macros are described in a JSON file and replayed with the native Win32
SendInput API. The program has a dry-run mode so macro files can be checked on
any platform before they are used on Windows.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Iterable


Action = dict[str, Any]


KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
WHEEL_DELTA = 120
VK_ESCAPE = 0x1B


KEYS: dict[str, int] = {
    "backspace": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "pause": 0x13,
    "capslock": 0x14,
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "insert": 0x2D,
    "delete": 0x2E,
    "win": 0x5B,
    "windows": 0x5B,
    "cmd": 0x5B,
    "menu": 0x5D,
    "numlock": 0x90,
    "scrolllock": 0x91,
    "printscreen": 0x2C,
}

for number in range(10):
    KEYS[str(number)] = 0x30 + number

for code in range(ord("a"), ord("z") + 1):
    KEYS[chr(code)] = code - 32

for number in range(1, 13):
    KEYS[f"f{number}"] = 0x70 + number - 1


class MousePoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]


class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", InputUnion)]


class MacroError(Exception):
    """Raised when a macro file or action is invalid."""


def load_config(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError as exc:
        raise MacroError(f"Macro file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MacroError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(config, dict):
        raise MacroError("The macro file must contain a JSON object.")

    macros = config.get("macros")
    if not isinstance(macros, dict) or not macros:
        raise MacroError("The macro file must define a non-empty 'macros' object.")

    for name, actions in macros.items():
        if not isinstance(name, str) or not name.strip():
            raise MacroError("Macro names must be non-empty strings.")
        validate_actions(actions, macro_name=name)

    return config


def validate_actions(actions: Any, macro_name: str = "macro") -> None:
    if not isinstance(actions, list) or not actions:
        raise MacroError(f"Macro '{macro_name}' must contain a non-empty action list.")

    for index, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            raise MacroError(f"Action {index} in '{macro_name}' must be an object.")

        action_type = action.get("type")
        if action_type not in {
            "wait",
            "key",
            "press",
            "hotkey",
            "type",
            "mouse_move",
            "mouse_click",
            "mouse_scroll",
        }:
            raise MacroError(f"Action {index} in '{macro_name}' has unknown type: {action_type!r}.")

        if action_type == "wait":
            require_number(action, "seconds", index, macro_name, minimum=0)
        elif action_type == "key":
            require_key(action, "key", index, macro_name)
            if action.get("event") not in {"down", "up"}:
                raise MacroError(f"Action {index} in '{macro_name}' key event must be 'down' or 'up'.")
        elif action_type == "press":
            require_key(action, "key", index, macro_name)
            require_optional_int(action, "times", index, macro_name, minimum=1)
            require_optional_number(action, "interval", index, macro_name, minimum=0)
        elif action_type == "hotkey":
            keys = action.get("keys")
            if not isinstance(keys, list) or not keys:
                raise MacroError(f"Action {index} in '{macro_name}' hotkey must define a non-empty keys list.")
            for key in keys:
                resolve_key(key, index, macro_name)
        elif action_type == "type":
            if not isinstance(action.get("text"), str):
                raise MacroError(f"Action {index} in '{macro_name}' type action must define text.")
            require_optional_number(action, "interval", index, macro_name, minimum=0)
        elif action_type == "mouse_move":
            require_int(action, "x", index, macro_name)
            require_int(action, "y", index, macro_name)
            require_optional_number(action, "duration", index, macro_name, minimum=0)
        elif action_type == "mouse_click":
            require_optional_int(action, "x", index, macro_name)
            require_optional_int(action, "y", index, macro_name)
            button = action.get("button", "left")
            if button not in {"left", "right", "middle"}:
                raise MacroError(f"Action {index} in '{macro_name}' mouse button must be left, right, or middle.")
            require_optional_int(action, "clicks", index, macro_name, minimum=1)
            require_optional_number(action, "interval", index, macro_name, minimum=0)
        elif action_type == "mouse_scroll":
            require_int(action, "amount", index, macro_name)


def require_key(action: Action, field: str, index: int, macro_name: str) -> None:
    resolve_key(action.get(field), index, macro_name)


def resolve_key(key: Any, index: int, macro_name: str) -> int:
    if not isinstance(key, str):
        raise MacroError(f"Action {index} in '{macro_name}' key value must be a string.")

    normalized = key.lower().replace("_", "").replace("-", "").strip()
    if normalized in KEYS:
        return KEYS[normalized]

    raise MacroError(f"Action {index} in '{macro_name}' uses unsupported key: {key!r}.")


def require_int(action: Action, field: str, index: int, macro_name: str, minimum: int | None = None) -> None:
    if field not in action:
        raise MacroError(f"Action {index} in '{macro_name}' must define '{field}'.")
    require_optional_int(action, field, index, macro_name, minimum)


def require_optional_int(
    action: Action,
    field: str,
    index: int,
    macro_name: str,
    minimum: int | None = None,
) -> None:
    if field not in action:
        return
    value = action[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise MacroError(f"Action {index} in '{macro_name}' field '{field}' must be an integer.")
    if minimum is not None and value < minimum:
        raise MacroError(f"Action {index} in '{macro_name}' field '{field}' must be at least {minimum}.")


def require_number(action: Action, field: str, index: int, macro_name: str, minimum: float | None = None) -> None:
    if field not in action:
        raise MacroError(f"Action {index} in '{macro_name}' must define '{field}'.")
    require_optional_number(action, field, index, macro_name, minimum)


def require_optional_number(
    action: Action,
    field: str,
    index: int,
    macro_name: str,
    minimum: float | None = None,
) -> None:
    if field not in action:
        return
    value = action[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MacroError(f"Action {index} in '{macro_name}' field '{field}' must be a number.")
    if not math.isfinite(value):
        raise MacroError(f"Action {index} in '{macro_name}' field '{field}' must be finite.")
    if minimum is not None and value < minimum:
        raise MacroError(f"Action {index} in '{macro_name}' field '{field}' must be at least {minimum}.")


def ensure_windows() -> None:
    if sys.platform != "win32":
        raise MacroError("Real macro playback requires Windows. Use --dry-run to preview on this platform.")


class WindowsInput:
    def __init__(self) -> None:
        ensure_windows()
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)

    def send_keyboard(self, vk: int = 0, scan: int = 0, flags: int = 0) -> None:
        extra = ctypes.c_ulong(0)
        event = Input(
            type=INPUT_KEYBOARD,
            ii=InputUnion(ki=KeyboardInput(vk, scan, flags, 0, ctypes.pointer(extra))),
        )
        self.send_input(event)

    def send_mouse(self, flags: int, data: int = 0, dx: int = 0, dy: int = 0) -> None:
        extra = ctypes.c_ulong(0)
        event = Input(
            type=INPUT_MOUSE,
            ii=InputUnion(mi=MouseInput(dx, dy, data, flags, 0, ctypes.pointer(extra))),
        )
        self.send_input(event)

    def send_input(self, event: Input) -> None:
        sent = self.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))
        if sent != 1:
            error_code = ctypes.get_last_error()
            raise ctypes.WinError(error_code)

    def set_cursor_pos(self, x: int, y: int) -> None:
        if not self.user32.SetCursorPos(x, y):
            error_code = ctypes.get_last_error()
            raise ctypes.WinError(error_code)

    def get_cursor_pos(self) -> tuple[int, int]:
        point = MousePoint()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            error_code = ctypes.get_last_error()
            raise ctypes.WinError(error_code)
        return point.x, point.y

    def escape_pressed(self) -> bool:
        return bool(self.user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)


class MacroPlayer:
    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.input = None if dry_run else WindowsInput()

    def play(self, actions: Iterable[Action], repeat: int = 1, start_delay: float = 0.0) -> None:
        if repeat < 1:
            raise MacroError("--repeat must be at least 1.")
        if start_delay < 0:
            raise MacroError("--delay must be at least 0.")

        if start_delay and self.dry_run:
            print(f"[dry-run] startup delay {start_delay} seconds")
        elif start_delay:
            self.wait(start_delay)

        for run_number in range(repeat):
            if self.dry_run:
                print(f"[dry-run] starting run {run_number + 1} of {repeat}")
            for action in actions:
                self.check_abort()
                self.perform(action)

    def perform(self, action: Action) -> None:
        action_type = action["type"]
        if self.dry_run:
            print(f"[dry-run] {describe_action(action)}")
            return

        if action_type == "wait":
            self.wait(float(action["seconds"]))
        elif action_type == "key":
            self.key_event(action["key"], action["event"])
        elif action_type == "press":
            times = int(action.get("times", 1))
            interval = float(action.get("interval", 0.05))
            for _ in range(times):
                self.press_key(action["key"])
                self.wait(interval)
        elif action_type == "hotkey":
            self.hotkey(action["keys"])
        elif action_type == "type":
            self.type_text(action["text"], float(action.get("interval", 0.02)))
        elif action_type == "mouse_move":
            self.move_mouse(int(action["x"]), int(action["y"]), float(action.get("duration", 0)))
        elif action_type == "mouse_click":
            self.click_mouse(
                button=action.get("button", "left"),
                x=action.get("x"),
                y=action.get("y"),
                clicks=int(action.get("clicks", 1)),
                interval=float(action.get("interval", 0.05)),
            )
        elif action_type == "mouse_scroll":
            self.scroll_mouse(int(action["amount"]))

    def wait(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check_abort()
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(0.05, remaining))

    def check_abort(self) -> None:
        if self.input is not None and self.input.escape_pressed():
            raise MacroError("Playback stopped because Esc was pressed.")

    def key_event(self, key: str, event: str) -> None:
        vk = resolve_key(key, 0, "runtime")
        flags = KEYEVENTF_KEYUP if event == "up" else 0
        self.input.send_keyboard(vk=vk, flags=flags)

    def press_key(self, key: str) -> None:
        self.key_event(key, "down")
        self.key_event(key, "up")

    def hotkey(self, keys: list[str]) -> None:
        for key in keys:
            self.key_event(key, "down")
            self.wait(0.02)
        for key in reversed(keys):
            self.key_event(key, "up")
            self.wait(0.02)

    def type_text(self, text: str, interval: float) -> None:
        for char in text:
            self.check_abort()
            scan = ord(char)
            self.input.send_keyboard(scan=scan, flags=KEYEVENTF_UNICODE)
            self.input.send_keyboard(scan=scan, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
            self.wait(interval)

    def move_mouse(self, x: int, y: int, duration: float) -> None:
        if duration <= 0:
            self.input.set_cursor_pos(x, y)
            return

        start_x, start_y = self.input.get_cursor_pos()
        steps = max(1, int(duration / 0.01))
        for step in range(1, steps + 1):
            self.check_abort()
            fraction = step / steps
            next_x = round(start_x + (x - start_x) * fraction)
            next_y = round(start_y + (y - start_y) * fraction)
            self.input.set_cursor_pos(next_x, next_y)
            self.wait(duration / steps)

    def click_mouse(
        self,
        button: str,
        x: int | None = None,
        y: int | None = None,
        clicks: int = 1,
        interval: float = 0.05,
    ) -> None:
        if x is not None and y is not None:
            self.input.set_cursor_pos(x, y)

        down, up = {
            "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
            "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
            "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
        }[button]

        for _ in range(clicks):
            self.input.send_mouse(down)
            self.input.send_mouse(up)
            self.wait(interval)

    def scroll_mouse(self, amount: int) -> None:
        self.input.send_mouse(MOUSEEVENTF_WHEEL, data=amount * WHEEL_DELTA)


def describe_action(action: Action) -> str:
    action_type = action["type"]
    if action_type == "wait":
        return f"wait {action['seconds']} seconds"
    if action_type == "key":
        return f"{action['event']} key {action['key']}"
    if action_type == "press":
        return f"press {action['key']} x{action.get('times', 1)}"
    if action_type == "hotkey":
        return "hotkey " + "+".join(action["keys"])
    if action_type == "type":
        return f"type {action['text']!r}"
    if action_type == "mouse_move":
        return f"move mouse to ({action['x']}, {action['y']})"
    if action_type == "mouse_click":
        suffix = ""
        if "x" in action and "y" in action:
            suffix = f" at ({action['x']}, {action['y']})"
        return f"{action.get('button', 'left')} click x{action.get('clicks', 1)}{suffix}"
    if action_type == "mouse_scroll":
        return f"scroll mouse {action['amount']}"
    return repr(action)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play keyboard and mouse macros on Windows 10.")
    parser.add_argument("macro_file", type=Path, help="Path to a JSON macro file.")
    parser.add_argument("--macro", help="Macro name to run. Defaults to the first macro in the file.")
    parser.add_argument("--list", action="store_true", help="List macros in the file and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without controlling the computer.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to replay the macro.")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds to wait before playback starts.")
    return parser


def choose_macro(config: dict[str, Any], name: str | None) -> tuple[str, list[Action]]:
    macros = config["macros"]
    if name is None:
        first_name = next(iter(macros))
        return first_name, macros[first_name]
    if name not in macros:
        available = ", ".join(macros)
        raise MacroError(f"Unknown macro '{name}'. Available macros: {available}")
    return name, macros[name]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.macro_file)
        if args.list:
            for macro_name in config["macros"]:
                print(macro_name)
            return 0

        macro_name, actions = choose_macro(config, args.macro)
        if not args.dry_run:
            print("Macro playback will start after the delay. Press Esc to stop playback.")
        print(f"Running macro: {macro_name}")

        player = MacroPlayer(dry_run=args.dry_run)
        player.play(actions, repeat=args.repeat, start_delay=args.delay)
    except (MacroError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
