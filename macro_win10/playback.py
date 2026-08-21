"""Macro playback using pyautogui."""

from __future__ import annotations

import time
from typing import Any

from .models import Macro, MacroEvent


KEY_ALIASES = {
    "alt_l": "alt",
    "alt_r": "alt",
    "alt_gr": "alt",
    "backspace": "backspace",
    "caps_lock": "capslock",
    "cmd": "win",
    "cmd_l": "win",
    "cmd_r": "win",
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "delete": "delete",
    "esc": "esc",
    "page_down": "pagedown",
    "page_up": "pageup",
    "print_screen": "printscreen",
    "scroll_lock": "scrolllock",
    "shift_l": "shift",
    "shift_r": "shift",
}


def _require_pyautogui() -> Any:
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError(
            "Playback requires pyautogui. Install dependencies with "
            "`python -m pip install -r requirements.txt`."
        ) from exc
    return pyautogui


def playback_key_name(key_name: str) -> str:
    lowered = key_name.lower()
    if lowered.startswith("key."):
        lowered = lowered[4:]
    if lowered.startswith("f") and lowered[1:].isdigit():
        return lowered
    return KEY_ALIASES.get(lowered, key_name)


def play_macro(
    macro: Macro,
    *,
    speed: float = 1.0,
    repeat: int = 1,
    start_delay: float = 3.0,
) -> None:
    """Replay a macro on the current desktop.

    Moving the mouse to the top-left corner of the screen triggers
    pyautogui's fail-safe exception and aborts playback.
    """

    if speed <= 0:
        raise ValueError("speed must be greater than zero")
    if repeat < 1:
        raise ValueError("repeat must be at least one")
    if start_delay < 0:
        raise ValueError("start_delay must be zero or greater")

    pyautogui = _require_pyautogui()
    pyautogui.PAUSE = 0
    pyautogui.FAILSAFE = True

    if start_delay:
        time.sleep(start_delay)

    for _ in range(repeat):
        _play_events(pyautogui, macro.events, speed=speed)


def _play_events(pyautogui: Any, events: list[MacroEvent], *, speed: float) -> None:
    previous_time = 0.0
    for event in events:
        wait_time = max(0.0, (event.time - previous_time) / speed)
        if wait_time:
            time.sleep(wait_time)
        _play_event(pyautogui, event)
        previous_time = event.time


def _play_event(pyautogui: Any, event: MacroEvent) -> None:
    data = event.data
    if event.type == "key_down":
        pyautogui.keyDown(playback_key_name(str(data["key"])))
    elif event.type == "key_up":
        pyautogui.keyUp(playback_key_name(str(data["key"])))
    elif event.type == "mouse_move":
        pyautogui.moveTo(int(data["x"]), int(data["y"]))
    elif event.type == "mouse_down":
        pyautogui.mouseDown(
            int(data["x"]),
            int(data["y"]),
            button=str(data.get("button", "left")),
        )
    elif event.type == "mouse_up":
        pyautogui.mouseUp(
            int(data["x"]),
            int(data["y"]),
            button=str(data.get("button", "left")),
        )
    elif event.type == "mouse_scroll":
        pyautogui.scroll(
            int(data.get("dy", 0)),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
        )
    else:
        raise ValueError(f"unsupported event type: {event.type}")
