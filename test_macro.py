import tempfile
import unittest
from pathlib import Path
from unittest import mock

import macro


class MacroConfigTests(unittest.TestCase):
    def write_config(self, text: str) -> Path:
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
        temp.write(text)
        temp.close()
        path = Path(temp.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_loads_valid_macro_file(self) -> None:
        path = self.write_config('{"macros": {"demo": [{"type": "press", "key": "enter"}]}}')

        config = macro.load_config(path)

        self.assertEqual(["demo"], list(config["macros"]))

    def test_rejects_missing_macros_object(self) -> None:
        path = self.write_config('{"version": 1}')

        with self.assertRaisesRegex(macro.MacroError, "macros"):
            macro.load_config(path)

    def test_rejects_unknown_key(self) -> None:
        path = self.write_config('{"macros": {"demo": [{"type": "press", "key": "hyper"}]}}')

        with self.assertRaisesRegex(macro.MacroError, "unsupported key"):
            macro.load_config(path)

    def test_choose_macro_defaults_to_first_macro(self) -> None:
        config = {
            "macros": {
                "first": [{"type": "wait", "seconds": 0}],
                "second": [{"type": "wait", "seconds": 0}],
            }
        }

        name, actions = macro.choose_macro(config, None)

        self.assertEqual("first", name)
        self.assertEqual([{"type": "wait", "seconds": 0}], actions)

    def test_choose_macro_reports_available_names(self) -> None:
        config = {"macros": {"demo": [{"type": "wait", "seconds": 0}]}}

        with self.assertRaisesRegex(macro.MacroError, "Available macros: demo"):
            macro.choose_macro(config, "missing")


class MacroPlayerDryRunTests(unittest.TestCase):
    def test_dry_run_prints_actions_without_windows_api(self) -> None:
        player = macro.MacroPlayer(dry_run=True)
        actions = [
            {"type": "hotkey", "keys": ["ctrl", "l"]},
            {"type": "type", "text": "hello"},
            {"type": "mouse_click", "button": "left", "clicks": 2},
        ]

        with mock.patch("builtins.print") as mocked_print:
            player.play(actions, repeat=1, start_delay=0)

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list)
        self.assertIn("hotkey ctrl+l", printed)
        self.assertIn("type 'hello'", printed)
        self.assertIn("left click x2", printed)


if __name__ == "__main__":
    unittest.main()
