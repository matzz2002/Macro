"""Helpers to convert between :mod:`pynput` objects and plain strings.

Recorded macros are stored as JSON, therefore the ``pynput`` key/button objects
have to be turned into strings when recording and reconstructed when playing a
macro back.
"""

from __future__ import annotations

from typing import Union

from pynput import keyboard, mouse

# A virtual-key code that has no printable character is stored as ``vk:<code>``.
_VK_PREFIX = "vk:"

KeyLike = Union[keyboard.Key, keyboard.KeyCode]


def key_to_str(key: KeyLike) -> str:
    """Serialize a ``pynput`` key to a stable string.

    * Named/special keys (Enter, Shift, ...) become their ``name`` (``"enter"``).
    * Printable characters become the character itself (``"a"``).
    * Anything else falls back to ``"vk:<code>"`` using the virtual-key code.
    """

    if isinstance(key, keyboard.Key):
        return key.name
    if isinstance(key, keyboard.KeyCode):
        if key.char is not None:
            return key.char
        if key.vk is not None:
            return f"{_VK_PREFIX}{key.vk}"
    return str(key)


def str_to_key(value: str) -> KeyLike:
    """Inverse of :func:`key_to_str`."""

    if value.startswith(_VK_PREFIX):
        return keyboard.KeyCode.from_vk(int(value[len(_VK_PREFIX):]))
    # Named special keys such as "enter", "space", "ctrl_l" ...
    special = getattr(keyboard.Key, value, None)
    if special is not None:
        return special
    return keyboard.KeyCode.from_char(value)


def button_to_str(button: mouse.Button) -> str:
    """Serialize a mouse button (``mouse.Button.left`` -> ``"left"``)."""

    return button.name


def str_to_button(value: str) -> mouse.Button:
    """Inverse of :func:`button_to_str`."""

    button = getattr(mouse.Button, value, None)
    if button is None:
        raise ValueError(f"Unknown mouse button: {value!r}")
    return button
