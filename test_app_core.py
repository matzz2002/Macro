import tempfile
import unittest
from pathlib import Path

from macro_app.action_tools import scale_delays
from macro_app.models import ActionType, AppData, Macro, MacroAction, Profile
from macro_app.storage import JsonStorage
from macro_app.validation import Hotkey, find_hotkey_conflicts, normalize_hotkey, validate_macro


class HotkeyValidationTests(unittest.TestCase):
    def test_normalizes_keyboard_hotkey(self) -> None:
        self.assertEqual("Ctrl + Shift + X", normalize_hotkey("ctrl + shift + x"))

    def test_supports_mouse_buttons(self) -> None:
        self.assertEqual(frozenset({"mouse4"}), Hotkey.parse("Mouse Button 4").key())
        self.assertEqual(frozenset({"mouse5"}), Hotkey.parse("Mouse Button 5").key())

    def test_detects_hotkey_conflict_with_panic_key(self) -> None:
        profile = Profile(name="Test", macros=[Macro(name="Stop conflict", hotkey="F12")])

        conflicts = find_hotkey_conflicts(profile, panic_hotkey="F12")

        self.assertIn(profile.macros[0].id, conflicts)


class MacroModelTests(unittest.TestCase):
    def test_macro_clone_clears_hotkey_and_copies_actions(self) -> None:
        macro = Macro(
            name="Demo",
            hotkey="F6",
            actions=[MacroAction(ActionType.DELAY, {"ms": 100})],
        )

        clone = macro.clone()
        clone.actions[0].params["ms"] = 250

        self.assertEqual("", clone.hotkey)
        self.assertEqual(100, macro.actions[0].params["ms"])
        self.assertEqual(250, clone.actions[0].params["ms"])

    def test_validate_macro_reports_bad_delay(self) -> None:
        macro = Macro(name="Bad", actions=[MacroAction(ActionType.DELAY, {"ms": -1})])

        self.assertTrue(any("opóźnienie" in error for error in validate_macro(macro)))


class ActionToolsTests(unittest.TestCase):
    def test_scales_all_delay_ranges(self) -> None:
        actions = [
            MacroAction(ActionType.DELAY, {"ms": 100}),
            MacroAction(ActionType.DELAY, {"ms": 100, "random_min_ms": 80, "random_max_ms": 120}),
            MacroAction(ActionType.KEY_PRESS, {"key": "a"}),
        ]

        updated = scale_delays(actions, 50)

        self.assertEqual(50, updated[0].params["ms"])
        self.assertEqual(40, updated[1].params["random_min_ms"])
        self.assertEqual(60, updated[1].params["random_max_ms"])
        self.assertEqual("a", updated[2].params["key"])


class StorageTests(unittest.TestCase):
    def test_saves_loads_and_exports_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JsonStorage(Path(temp_dir))
            data = AppData.default()
            storage.save_data(data)

            loaded = storage.load_data()
            export_path = Path(temp_dir) / "profile.json"
            storage.export_profile(loaded.active_profile(), export_path)
            imported = storage.import_profile(export_path)

            self.assertEqual(loaded.active_profile().name, imported.name)


if __name__ == "__main__":
    unittest.main()
