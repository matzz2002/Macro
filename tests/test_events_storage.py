"""Tests that do not require a display or the pynput backend.

These cover the pure-data layer (events + storage), which is the part most
worth protecting against regressions.  Recorder/player/GUI need a real input
backend and are therefore validated manually on Windows.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the package importable when the tests are run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from macro_recorder.events import (  # noqa: E402
    KEY_PRESS,
    MOUSE_CLICK,
    MOUSE_MOVE,
    Event,
    Macro,
)
from macro_recorder.storage import load_macro, save_macro  # noqa: E402


def _sample_macro() -> Macro:
    events = [
        Event(kind=KEY_PRESS, time=0.0, key="a"),
        Event(kind=MOUSE_MOVE, time=0.5, x=10, y=20),
        Event(
            kind=MOUSE_CLICK,
            time=0.75,
            x=10,
            y=20,
            button="left",
            pressed=True,
        ),
    ]
    return Macro(name="Sample", events=events, captured_mouse_move=True)


def test_event_roundtrip() -> None:
    event = Event(kind=MOUSE_CLICK, time=1.25, x=5, y=6, button="right", pressed=False)
    restored = Event.from_dict(event.to_dict())
    assert restored == event


def test_event_to_dict_drops_none_fields() -> None:
    event = Event(kind=KEY_PRESS, time=1.0, key="b")
    data = event.to_dict()
    assert data == {"kind": KEY_PRESS, "time": 1.0, "key": "b"}


def test_invalid_kind_rejected() -> None:
    try:
        Event(kind="nope", time=0.0)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for invalid kind")


def test_macro_duration() -> None:
    macro = _sample_macro()
    assert macro.duration == 0.75
    assert Macro().duration == 0.0


def test_storage_roundtrip(tmp_path: Path) -> None:
    macro = _sample_macro()
    path = tmp_path / "macro.json"
    save_macro(path, macro)

    loaded = load_macro(path)
    assert loaded.name == macro.name
    assert loaded.captured_mouse_move is True
    assert [e.to_dict() for e in loaded.events] == [
        e.to_dict() for e in macro.events
    ]


def test_load_rejects_non_macro(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"foo": 1}', encoding="utf-8")
    try:
        load_macro(path)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for non-macro file")


if __name__ == "__main__":
    # Allow running without pytest installed.
    import tempfile

    test_event_roundtrip()
    test_event_to_dict_drops_none_fields()
    test_invalid_kind_rejected()
    test_macro_duration()
    with tempfile.TemporaryDirectory() as tmp:
        test_storage_roundtrip(Path(tmp))
        test_load_rejects_non_macro(Path(tmp))
    print("All tests passed.")
