from __future__ import annotations

from .models import ActionType, MacroAction


def action_label(action: MacroAction) -> str:
    params = action.params
    if action.type == ActionType.KEY_DOWN:
        return f"Key Down -> {params.get('key', '')}"
    if action.type == ActionType.KEY_UP:
        return f"Key Up -> {params.get('key', '')}"
    if action.type == ActionType.KEY_PRESS:
        return f"Key Press -> {params.get('key', '')}"
    if action.type == ActionType.HOTKEY:
        return "Hotkey -> " + " + ".join(str(key) for key in params.get("keys", []))
    if action.type == ActionType.MOUSE_CLICK:
        pos = ""
        if isinstance(params.get("x"), int) and isinstance(params.get("y"), int):
            pos = f" @ {params['x']}, {params['y']}"
        return f"Mouse Click -> {params.get('button', 'left')} x{params.get('clicks', 1)}{pos}"
    if action.type == ActionType.MOUSE_MOVE:
        return f"Mouse Move -> {params.get('x', 0)}, {params.get('y', 0)}"
    if action.type == ActionType.DELAY:
        if "random_min_ms" in params and "random_max_ms" in params:
            return f"Delay -> {params['random_min_ms']}-{params['random_max_ms']} ms"
        return f"Delay -> {params.get('ms', 0)} ms"
    if action.type == ActionType.LOOP:
        return f"Loop -> {params.get('count', 1)}x ({len(params.get('actions', []))} akcji)"
    return action.type.value


def default_action(action_type: ActionType) -> MacroAction:
    defaults = {
        ActionType.KEY_DOWN: {"key": "w"},
        ActionType.KEY_UP: {"key": "w"},
        ActionType.KEY_PRESS: {"key": "enter"},
        ActionType.HOTKEY: {"keys": ["ctrl", "c"]},
        ActionType.MOUSE_CLICK: {"button": "left", "clicks": 1},
        ActionType.MOUSE_MOVE: {"x": 500, "y": 300, "duration_ms": 0},
        ActionType.DELAY: {"ms": 100},
        ActionType.LOOP: {"count": 2, "actions": [{"type": "delay", "params": {"ms": 100}}]},
    }
    return MacroAction(action_type, defaults[action_type].copy())


def scale_delays(actions: list[MacroAction], percent: int) -> list[MacroAction]:
    factor = max(0, percent) / 100
    updated: list[MacroAction] = []
    for action in actions:
        clone = action.clone()
        if clone.type == ActionType.DELAY:
            if "ms" in clone.params:
                clone.params["ms"] = round(int(clone.params["ms"]) * factor)
            if "random_min_ms" in clone.params:
                clone.params["random_min_ms"] = round(int(clone.params["random_min_ms"]) * factor)
            if "random_max_ms" in clone.params:
                clone.params["random_max_ms"] = round(int(clone.params["random_max_ms"]) * factor)
        updated.append(clone)
    return updated
