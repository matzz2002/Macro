"""Serializable data models for recorded input events.

A recorded macro is an ordered list of :class:`Event` objects.  Every event
stores the number of seconds that elapsed between the start of the recording and
the moment the event happened (``time``).  Keeping an absolute-from-start offset
(rather than a delay between consecutive events) makes it trivial to play a
macro back at a different speed without accumulating rounding error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Event kinds.  Kept as module level constants so callers do not sprinkle magic
# strings around the code base.
KEY_PRESS = "key_press"
KEY_RELEASE = "key_release"
MOUSE_MOVE = "mouse_move"
MOUSE_CLICK = "mouse_click"
MOUSE_SCROLL = "mouse_scroll"

VALID_KINDS = frozenset(
    {KEY_PRESS, KEY_RELEASE, MOUSE_MOVE, MOUSE_CLICK, MOUSE_SCROLL}
)


@dataclass
class Event:
    """A single recorded input event.

    Only the fields relevant to a given ``kind`` are populated; the rest stay
    ``None`` so the JSON representation is compact and self describing.
    """

    kind: str
    time: float

    # Keyboard events.
    key: Optional[str] = None

    # Mouse events.
    x: Optional[int] = None
    y: Optional[int] = None
    button: Optional[str] = None
    pressed: Optional[bool] = None
    dx: Optional[int] = None
    dy: Optional[int] = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"Unknown event kind: {self.kind!r}")

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON friendly dict with ``None`` fields removed."""

        data: Dict[str, Any] = {"kind": self.kind, "time": round(self.time, 6)}
        for name in ("key", "x", "y", "button", "pressed", "dx", "dy"):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            kind=data["kind"],
            time=float(data["time"]),
            key=data.get("key"),
            x=data.get("x"),
            y=data.get("y"),
            button=data.get("button"),
            pressed=data.get("pressed"),
            dx=data.get("dx"),
            dy=data.get("dy"),
        )

    def describe(self) -> str:
        """Return a short, human readable one line summary of the event."""

        if self.kind == KEY_PRESS:
            return f"Key press: {self.key}"
        if self.kind == KEY_RELEASE:
            return f"Key release: {self.key}"
        if self.kind == MOUSE_MOVE:
            return f"Mouse move -> ({self.x}, {self.y})"
        if self.kind == MOUSE_CLICK:
            action = "down" if self.pressed else "up"
            return f"Mouse {self.button} {action} @ ({self.x}, {self.y})"
        if self.kind == MOUSE_SCROLL:
            return f"Scroll ({self.dx}, {self.dy}) @ ({self.x}, {self.y})"
        return self.kind


@dataclass
class Macro:
    """A named collection of events plus a little metadata."""

    name: str = "Untitled macro"
    events: List[Event] = field(default_factory=list)
    created_at: Optional[str] = None
    captured_mouse_move: bool = False
    app_version: Optional[str] = None

    @property
    def duration(self) -> float:
        """Length of the macro in seconds (0 when empty)."""

        return self.events[-1].time if self.events else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "captured_mouse_move": self.captured_mouse_move,
            "app_version": self.app_version,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Macro":
        return cls(
            name=data.get("name", "Untitled macro"),
            events=[Event.from_dict(item) for item in data.get("events", [])],
            created_at=data.get("created_at"),
            captured_mouse_move=data.get("captured_mouse_move", False),
            app_version=data.get("app_version"),
        )
