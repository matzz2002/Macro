"""Data model for recorded keyboard and mouse macros."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


SUPPORTED_EVENT_TYPES = {
    "key_down",
    "key_up",
    "mouse_move",
    "mouse_down",
    "mouse_up",
    "mouse_scroll",
}


@dataclass(frozen=True)
class MacroEvent:
    """One timestamped keyboard or mouse event in a macro."""

    time: float
    type: str
    data: dict[str, Any]

    def __post_init__(self) -> None:
        if self.time < 0:
            raise ValueError("event time must be zero or greater")
        if self.type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported event type: {self.type}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": round(self.time, 6),
            "type": self.type,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MacroEvent":
        try:
            event_time = float(raw["time"])
            event_type = str(raw["type"])
            data = dict(raw["data"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid macro event: {raw!r}") from exc
        return cls(time=event_time, type=event_type, data=data)


@dataclass
class Macro:
    """A complete macro recording."""

    name: str = "Untitled Macro"
    events: list[MacroEvent] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: int = 1

    @property
    def duration(self) -> float:
        if not self.events:
            return 0.0
        return self.events[-1].time

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "created_at": self.created_at,
            "duration": round(self.duration, 6),
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Macro":
        try:
            version = int(raw.get("version", 1))
            name = str(raw.get("name", "Untitled Macro"))
            created_at = str(raw.get("created_at", ""))
            events = [MacroEvent.from_dict(item) for item in raw.get("events", [])]
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid macro file") from exc

        if version != 1:
            raise ValueError(f"unsupported macro version: {version}")

        return cls(
            name=name,
            events=events,
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
            version=version,
        )
