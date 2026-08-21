from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ActionType, Macro, MacroAction, Profile


class ValidationError(ValueError):
    pass


MODIFIERS = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "shift": "shift",
    "alt": "alt",
    "win": "win",
    "windows": "win",
    "cmd": "win",
}

NAMED_KEYS = {
    "backspace",
    "tab",
    "enter",
    "return",
    "esc",
    "escape",
    "space",
    "delete",
    "insert",
    "home",
    "end",
    "pageup",
    "pagedown",
    "up",
    "down",
    "left",
    "right",
    "capslock",
    "numlock",
    "printscreen",
}

MOUSE_ALIASES = {
    "mouse4": "mouse4",
    "mouse5": "mouse5",
    "mousebutton4": "mouse4",
    "mousebutton5": "mouse5",
    "xbutton1": "mouse4",
    "xbutton2": "mouse5",
}


@dataclass(frozen=True)
class Hotkey:
    tokens: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> "Hotkey":
        raw_parts = [part.strip() for part in re.split(r"\+", value or "") if part.strip()]
        if not raw_parts:
            raise ValidationError("Skrót nie może być pusty.")

        tokens: list[str] = []
        for raw in raw_parts:
            token = normalize_key_token(raw)
            if token in tokens:
                raise ValidationError(f"Skrót zawiera duplikat klawisza: {raw}.")
            tokens.append(token)

        return cls(tuple(sorted(tokens)))

    def display(self) -> str:
        return " + ".join(display_token(token) for token in self.tokens)

    def key(self) -> frozenset[str]:
        return frozenset(self.tokens)


def normalize_key_token(raw: str) -> str:
    compact = raw.lower().replace(" ", "").replace("_", "").replace("-", "")
    if compact in MODIFIERS:
        return MODIFIERS[compact]
    if compact in MOUSE_ALIASES:
        return MOUSE_ALIASES[compact]
    if compact in {"leftmouse", "mouseleft"}:
        return "mouse_left"
    if compact in {"rightmouse", "mouseright"}:
        return "mouse_right"
    if compact in {"middlemouse", "mousemiddle"}:
        return "mouse_middle"
    if re.fullmatch(r"f([1-9]|1[0-2])", compact):
        return compact
    if compact in NAMED_KEYS:
        return {"return": "enter", "escape": "esc"}.get(compact, compact)
    if len(compact) == 1 and compact.isprintable():
        return compact
    raise ValidationError(f"Nieobsługiwany klawisz skrótu: {raw}.")


def display_token(token: str) -> str:
    names = {
        "ctrl": "Ctrl",
        "shift": "Shift",
        "alt": "Alt",
        "win": "Win",
        "esc": "Esc",
        "enter": "Enter",
        "space": "Space",
        "mouse4": "Mouse Button 4",
        "mouse5": "Mouse Button 5",
        "mouse_left": "Mouse Left",
        "mouse_right": "Mouse Right",
        "mouse_middle": "Mouse Middle",
    }
    if token in names:
        return names[token]
    if re.fullmatch(r"f([1-9]|1[0-2])", token):
        return token.upper()
    if len(token) == 1:
        return token.upper()
    return token.title()


def normalize_hotkey(value: str) -> str:
    return Hotkey.parse(value).display()


def find_hotkey_conflicts(profile: Profile, panic_hotkey: str = "F12") -> dict[str, list[str]]:
    conflicts: dict[str, list[str]] = {}
    seen: dict[frozenset[str], str] = {}

    try:
        panic_key = Hotkey.parse(panic_hotkey).key()
        seen[panic_key] = "Panic key"
    except ValidationError:
        pass

    for macro in profile.macros:
        if not macro.hotkey.strip():
            continue
        try:
            key = Hotkey.parse(macro.hotkey).key()
        except ValidationError as exc:
            conflicts.setdefault(macro.id, []).append(str(exc))
            continue
        if key in seen:
            conflicts.setdefault(macro.id, []).append(f"Konflikt ze skrótem: {seen[key]}.")
        else:
            seen[key] = macro.name

    return conflicts


def validate_macro(macro: Macro) -> list[str]:
    errors: list[str] = []
    if not macro.name.strip():
        errors.append("Makro musi mieć nazwę.")
    if macro.repeat_count < 1:
        errors.append("Liczba powtórzeń musi być większa od zera.")
    if macro.hotkey.strip():
        try:
            normalize_hotkey(macro.hotkey)
        except ValidationError as exc:
            errors.append(str(exc))
    for index, action in enumerate(macro.actions, start=1):
        errors.extend(validate_action(action, index))
    return errors


def validate_action(action: MacroAction, index: int) -> list[str]:
    errors: list[str] = []
    params = action.params
    prefix = f"Akcja {index}: "

    if action.type in {ActionType.KEY_DOWN, ActionType.KEY_UP, ActionType.KEY_PRESS}:
        if not str(params.get("key", "")).strip():
            errors.append(prefix + "brakuje klawisza.")
    elif action.type == ActionType.HOTKEY:
        keys = params.get("keys")
        if not isinstance(keys, list) or not keys:
            errors.append(prefix + "kombinacja musi mieć co najmniej jeden klawisz.")
    elif action.type == ActionType.MOUSE_CLICK:
        if params.get("button", "left") not in {"left", "right", "middle", "x1", "x2"}:
            errors.append(prefix + "nieobsługiwany przycisk myszy.")
    elif action.type == ActionType.MOUSE_MOVE:
        if not isinstance(params.get("x"), int) or not isinstance(params.get("y"), int):
            errors.append(prefix + "ruch myszy wymaga współrzędnych x i y.")
    elif action.type == ActionType.DELAY:
        ms = params.get("ms", 0)
        if not isinstance(ms, int) or ms < 0:
            errors.append(prefix + "opóźnienie musi być liczbą milisekund >= 0.")
        random_min = params.get("random_min_ms")
        random_max = params.get("random_max_ms")
        if random_min is not None or random_max is not None:
            if not isinstance(random_min, int) or not isinstance(random_max, int) or random_min < 0 or random_max < random_min:
                errors.append(prefix + "losowy zakres opóźnienia jest nieprawidłowy.")
    elif action.type == ActionType.LOOP:
        count = params.get("count", 1)
        actions = params.get("actions", [])
        if not isinstance(count, int) or count < 1:
            errors.append(prefix + "pętla wymaga liczby powtórzeń >= 1.")
        if not isinstance(actions, list):
            errors.append(prefix + "pętla wymaga listy akcji.")

    return errors
