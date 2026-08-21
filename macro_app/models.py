from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = 1


def new_id() -> str:
    return uuid4().hex


class ActionType(str, Enum):
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    KEY_PRESS = "key_press"
    HOTKEY = "hotkey"
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    DELAY = "delay"
    LOOP = "loop"


class RunMode(str, Enum):
    ONCE = "once"
    REPEAT_COUNT = "repeat_count"
    TOGGLE = "toggle"
    HOLD = "hold"


@dataclass
class MacroAction:
    type: ActionType
    params: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type.value, "params": self.params}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MacroAction":
        return cls(
            id=str(data.get("id") or new_id()),
            type=ActionType(data["type"]),
            params=dict(data.get("params", {})),
        )

    def clone(self) -> "MacroAction":
        return MacroAction(type=self.type, params=deep_copy(self.params))


@dataclass
class Macro:
    name: str
    id: str = field(default_factory=new_id)
    color: str = "#7c3aed"
    icon: str = "bolt"
    hotkey: str = ""
    run_mode: RunMode = RunMode.ONCE
    repeat_count: int = 1
    stop_on_hotkey_release: bool = False
    actions: list[MacroAction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "icon": self.icon,
            "hotkey": self.hotkey,
            "run_mode": self.run_mode.value,
            "repeat_count": self.repeat_count,
            "stop_on_hotkey_release": self.stop_on_hotkey_release,
            "actions": [action.to_dict() for action in self.actions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Macro":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name") or "Nowe makro"),
            color=str(data.get("color") or "#7c3aed"),
            icon=str(data.get("icon") or "bolt"),
            hotkey=str(data.get("hotkey") or ""),
            run_mode=RunMode(data.get("run_mode") or RunMode.ONCE.value),
            repeat_count=max(1, int(data.get("repeat_count") or 1)),
            stop_on_hotkey_release=bool(data.get("stop_on_hotkey_release", False)),
            actions=[MacroAction.from_dict(item) for item in data.get("actions", [])],
        )

    def clone(self, name: str | None = None) -> "Macro":
        return Macro(
            name=name or f"{self.name} kopia",
            color=self.color,
            icon=self.icon,
            hotkey="",
            run_mode=self.run_mode,
            repeat_count=self.repeat_count,
            stop_on_hotkey_release=self.stop_on_hotkey_release,
            actions=[action.clone() for action in self.actions],
        )


@dataclass
class Profile:
    name: str
    id: str = field(default_factory=new_id)
    macros: list[Macro] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "macros": [macro.to_dict() for macro in self.macros]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name") or "Domyślny"),
            macros=[Macro.from_dict(item) for item in data.get("macros", [])],
        )

    def clone(self, name: str | None = None) -> "Profile":
        return Profile(name=name or f"{self.name} kopia", macros=[macro.clone() for macro in self.macros])


@dataclass
class AppData:
    profiles: list[Profile] = field(default_factory=list)
    active_profile_id: str = ""
    schema_version: int = SCHEMA_VERSION

    def ensure_defaults(self) -> None:
        if not self.profiles:
            starter = Macro(
                name="Notatnik demo",
                hotkey="F6",
                actions=[
                    MacroAction(ActionType.HOTKEY, {"keys": ["win", "r"]}),
                    MacroAction(ActionType.DELAY, {"ms": 200}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "n"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "o"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "t"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "e"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "p"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "a"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "d"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "enter"}),
                    MacroAction(ActionType.DELAY, {"ms": 800}),
                    MacroAction(ActionType.HOTKEY, {"keys": ["shift", "h"]}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "i"}),
                    MacroAction(ActionType.KEY_PRESS, {"key": "!"}),
                ],
            )
            self.profiles = [Profile(name="Gaming", macros=[starter]), Profile(name="Praca")]
        if not self.active_profile_id or not any(profile.id == self.active_profile_id for profile in self.profiles):
            self.active_profile_id = self.profiles[0].id

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_profile_id": self.active_profile_id,
            "profiles": [profile.to_dict() for profile in self.profiles],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppData":
        app_data = cls(
            schema_version=int(data.get("schema_version") or SCHEMA_VERSION),
            active_profile_id=str(data.get("active_profile_id") or ""),
            profiles=[Profile.from_dict(item) for item in data.get("profiles", [])],
        )
        app_data.ensure_defaults()
        return app_data

    @classmethod
    def default(cls) -> "AppData":
        data = cls()
        data.ensure_defaults()
        return data

    def active_profile(self) -> Profile:
        self.ensure_defaults()
        for profile in self.profiles:
            if profile.id == self.active_profile_id:
                return profile
        return self.profiles[0]


@dataclass
class AppSettings:
    theme: str = "dark"
    panic_hotkey: str = "F12"
    minimize_to_tray: bool = True
    start_with_windows: bool = False
    record_mouse_moves: bool = False
    mouse_move_interval_ms: int = 35
    autosave: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "panic_hotkey": self.panic_hotkey,
            "minimize_to_tray": self.minimize_to_tray,
            "start_with_windows": self.start_with_windows,
            "record_mouse_moves": self.record_mouse_moves,
            "mouse_move_interval_ms": self.mouse_move_interval_ms,
            "autosave": self.autosave,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        return cls(
            theme=str(data.get("theme") or "dark"),
            panic_hotkey=str(data.get("panic_hotkey") or "F12"),
            minimize_to_tray=bool(data.get("minimize_to_tray", True)),
            start_with_windows=bool(data.get("start_with_windows", False)),
            record_mouse_moves=bool(data.get("record_mouse_moves", False)),
            mouse_move_interval_ms=max(10, int(data.get("mouse_move_interval_ms") or 35)),
            autosave=bool(data.get("autosave", True)),
        )


def deep_copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [deep_copy(item) for item in value]
    return value
