import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from macro_win10.models import Macro, MacroEvent
from macro_win10.playback import playback_key_name
from macro_win10.storage import load_macro, save_macro


class MacroFileTests(unittest.TestCase):
    def test_macro_round_trip(self) -> None:
        macro = Macro(
            name="Round Trip",
            events=[
                MacroEvent(time=0.0, type="key_down", data={"key": "a"}),
                MacroEvent(time=0.1, type="key_up", data={"key": "a"}),
                MacroEvent(time=0.2, type="mouse_move", data={"x": 100, "y": 200}),
            ],
        )

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "macro.json"
            save_macro(macro, path)
            loaded = load_macro(path)

        self.assertEqual(loaded.name, "Round Trip")
        self.assertEqual(loaded.duration, 0.2)
        self.assertEqual(
            [event.to_dict() for event in loaded.events],
            [event.to_dict() for event in macro.events],
        )

    def test_invalid_event_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported event type"):
            MacroEvent(time=0.0, type="network_request", data={})

    def test_unknown_macro_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported macro version"):
            Macro.from_dict({"version": 99, "events": []})

    def test_key_aliases_match_pyautogui_names(self) -> None:
        self.assertEqual(playback_key_name("ctrl_l"), "ctrl")
        self.assertEqual(playback_key_name("Key.page_down"), "pagedown")
        self.assertEqual(playback_key_name("f8"), "f8")
        self.assertEqual(playback_key_name("a"), "a")


if __name__ == "__main__":
    unittest.main()
