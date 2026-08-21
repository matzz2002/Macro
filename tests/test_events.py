"""Tests for the serializable event model and JSON storage.

These tests intentionally avoid importing :mod:`macro_recorder.recorder` and
:mod:`macro_recorder.player`, which require ``pynput`` and a real display, so
they run in any headless CI environment.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from macro_recorder.events import (  # noqa: E402
    KeyEvent,
    Macro,
    MouseClickEvent,
    MouseMoveEvent,
    MouseScrollEvent,
    event_from_dict,
    summarize,
)
from macro_recorder.storage import load_macro, save_macro  # noqa: E402


class EventModelTests(unittest.TestCase):
    def _sample_macro(self) -> Macro:
        macro = Macro(name="sample")
        macro.add(KeyEvent(time=0.1, key="a", pressed=True))
        macro.add(KeyEvent(time=0.2, key="a", pressed=False))
        macro.add(MouseMoveEvent(time=0.3, x=10, y=20))
        macro.add(MouseClickEvent(time=0.4, x=10, y=20, button="Button.left", pressed=True))
        macro.add(MouseClickEvent(time=0.5, x=10, y=20, button="Button.left", pressed=False))
        macro.add(MouseScrollEvent(time=0.6, x=10, y=20, dx=0, dy=-2))
        return macro

    def test_event_round_trip(self) -> None:
        events = [
            KeyEvent(time=1.0, key="Key.enter", pressed=True),
            MouseMoveEvent(time=2.0, x=5, y=6),
            MouseClickEvent(time=3.0, x=5, y=6, button="Button.right", pressed=False),
            MouseScrollEvent(time=4.0, x=5, y=6, dx=1, dy=-1),
        ]
        for event in events:
            restored = event_from_dict(event.to_dict())
            self.assertEqual(restored.to_dict(), event.to_dict())
            self.assertEqual(restored.type, event.type)

    def test_unknown_event_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            event_from_dict({"type": "nope", "time": 0.0})

    def test_macro_duration_and_len(self) -> None:
        macro = self._sample_macro()
        self.assertEqual(len(macro), 6)
        self.assertAlmostEqual(macro.duration, 0.6)
        self.assertEqual(Macro().duration, 0.0)

    def test_macro_dict_round_trip(self) -> None:
        macro = self._sample_macro()
        restored = Macro.from_dict(macro.to_dict())
        self.assertEqual(restored.name, macro.name)
        self.assertEqual(len(restored), len(macro))
        self.assertEqual(
            [e.to_dict() for e in restored.events],
            [e.to_dict() for e in macro.events],
        )

    def test_from_dict_sorts_events(self) -> None:
        data = {
            "name": "unsorted",
            "events": [
                {"type": "key", "time": 0.5, "key": "b", "pressed": True},
                {"type": "key", "time": 0.1, "key": "a", "pressed": True},
            ],
        }
        macro = Macro.from_dict(data)
        self.assertEqual([e.time for e in macro.events], [0.1, 0.5])

    def test_storage_round_trip(self) -> None:
        macro = self._sample_macro()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nested", "macro.json")
            save_macro(macro, path)
            self.assertTrue(os.path.exists(path))
            loaded = load_macro(path)
        self.assertEqual(len(loaded), len(macro))
        self.assertEqual(loaded.name, macro.name)

    def test_summarize(self) -> None:
        summary = summarize(self._sample_macro())
        self.assertIn("sample", summary)
        self.assertIn("6 events", summary)


if __name__ == "__main__":
    unittest.main()
