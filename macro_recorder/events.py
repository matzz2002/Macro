"""Serializable event model used by the recorder and player.

A *macro* is an ordered list of :class:`MacroEvent` objects.  Each event stores
the time (in seconds, relative to the start of the recording) at which it
occurred, so playback can faithfully reproduce the original timing.

The model is intentionally free of any ``pynput`` types so that a macro can be
serialized to plain JSON and inspected/edited by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Individual event types
# --------------------------------------------------------------------------- #
@dataclass
class MacroEvent:
    """Base class for every event in a macro.

    ``time`` is the number of seconds elapsed since the start of the recording.
    """

    time: float
    type: str = field(init=False, default="base")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type
        return data


@dataclass
class KeyEvent(MacroEvent):
    """A keyboard key press or release.

    ``key`` is a portable string representation, e.g. ``"a"``, ``"Key.enter"``
    or ``"Key.ctrl_l"``.
    """

    key: str = ""
    pressed: bool = True

    def __post_init__(self) -> None:
        self.type = "key"


@dataclass
class MouseMoveEvent(MacroEvent):
    """Absolute mouse movement to screen coordinates ``(x, y)``."""

    x: int = 0
    y: int = 0

    def __post_init__(self) -> None:
        self.type = "mouse_move"


@dataclass
class MouseClickEvent(MacroEvent):
    """A mouse button press or release at ``(x, y)``.

    ``button`` is a portable string such as ``"Button.left"``.
    """

    x: int = 0
    y: int = 0
    button: str = "Button.left"
    pressed: bool = True

    def __post_init__(self) -> None:
        self.type = "mouse_click"


@dataclass
class MouseScrollEvent(MacroEvent):
    """A scroll wheel event at ``(x, y)`` with horizontal/vertical deltas."""

    x: int = 0
    y: int = 0
    dx: int = 0
    dy: int = 0

    def __post_init__(self) -> None:
        self.type = "mouse_scroll"


# Registry that maps a serialized ``type`` back to its dataclass.
_EVENT_TYPES = {
    "key": KeyEvent,
    "mouse_move": MouseMoveEvent,
    "mouse_click": MouseClickEvent,
    "mouse_scroll": MouseScrollEvent,
}


def event_from_dict(data: Dict[str, Any]) -> MacroEvent:
    """Reconstruct a :class:`MacroEvent` from its dictionary form."""

    event_type = data.get("type")
    cls = _EVENT_TYPES.get(event_type)
    if cls is None:
        raise ValueError(f"Unknown event type: {event_type!r}")

    # Drop the discriminator; it is set in ``__post_init__``.
    kwargs = {k: v for k, v in data.items() if k != "type"}
    return cls(**kwargs)


# --------------------------------------------------------------------------- #
# The macro container
# --------------------------------------------------------------------------- #
@dataclass
class Macro:
    """An ordered collection of :class:`MacroEvent` objects plus metadata."""

    name: str = "Untitled macro"
    events: List[MacroEvent] = field(default_factory=list)
    version: int = 1

    # ------------------------------------------------------------------ #
    def add(self, event: MacroEvent) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()

    @property
    def duration(self) -> float:
        """Total length of the macro in seconds (0 for an empty macro)."""

        if not self.events:
            return 0.0
        return max(event.time for event in self.events)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.events)

    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Macro":
        macro = cls(
            name=data.get("name", "Untitled macro"),
            version=int(data.get("version", 1)),
        )
        for raw in data.get("events", []):
            macro.add(event_from_dict(raw))
        # Guarantee chronological order regardless of file contents.
        macro.events.sort(key=lambda e: e.time)
        return macro


def summarize(macro: Macro) -> str:
    """Return a short human-readable summary of a macro."""

    counts: Dict[str, int] = {}
    for event in macro.events:
        counts[event.type] = counts.get(event.type, 0) + 1

    parts = [f"{count}x {name}" for name, count in sorted(counts.items())]
    body = ", ".join(parts) if parts else "empty"
    return f"'{macro.name}': {len(macro)} events ({body}), {macro.duration:.2f}s"
