# Macro Recorder for Windows 10

A lightweight keyboard **and** mouse macro tool for Windows 10. Record what you
type and where you click, then replay it as many times as you like — faster,
slower, or on an endless loop. It ships with both a simple graphical app and a
scriptable command line interface.

## Features

- **Records everything** — key presses/releases, mouse movement, clicks and
  scrolling, each with precise timing.
- **Faithful playback** — replay at the original speed, or use a speed
  multiplier and repeat count (including infinite loop).
- **Global hotkeys** — control recording/playback without switching windows:
  - `F9` — start recording
  - `F10` — stop recording / stop playback
  - `F11` — play the current macro
- **Save & load** — macros are stored as human‑readable JSON so they are easy to
  share, edit and version control.
- **GUI and CLI** — use the point‑and‑click window, or automate from scripts and
  scheduled tasks.
- **Optional mouse‑move capture** with throttling to keep recordings small.

## Requirements

- Windows 10 (also works on macOS/Linux, but designed and tested for Windows 10)
- Python 3.8+
- [`pynput`](https://pypi.org/project/pynput/) (installed via `requirements.txt`)

`tkinter` — used by the GUI — ships with the standard Python installer for
Windows, so there is nothing extra to install.

## Installation

```bash
# From the project folder
python -m venv .venv
.venv\Scripts\activate        # PowerShell / cmd on Windows
pip install -r requirements.txt
```

## Usage

### Graphical app

```bash
python run.py
# or
python -m macro_recorder
```

1. (Optional) untick **Record mouse movement** if you only care about clicks.
2. Press **Record (F9)** and perform your actions.
3. Press **Stop (F10)** when finished.
4. Set a **Speed** / **Repeat** count and press **Play (F11)**.
5. Use **Save…** / **Load…** to keep macros for later.

The hotkeys work even when the window is in the background, so you can record
and replay while another application is focused.

### Command line

Record until you press `Esc`:

```bash
python -m macro_recorder.cli record -o macros/login.json
```

Play it back twice at double speed (with a 3‑second countdown):

```bash
python -m macro_recorder.cli play macros/login.json --speed 2 --repeat 2
```

Loop forever until you press `Ctrl+C`:

```bash
python -m macro_recorder.cli play macros/login.json --repeat 0
```

Inspect a macro file:

```bash
python -m macro_recorder.cli info macros/login.json --verbose
```

Run `python -m macro_recorder.cli <command> --help` for every option.

## Using it as a library

```python
from macro_recorder import MacroRecorder, MacroPlayer, save_macro, load_macro

recorder = MacroRecorder()
recorder.start()
# ... do things ...
macro = recorder.stop()
save_macro("macros/demo.json", macro)

MacroPlayer().play(load_macro("macros/demo.json"), speed=1.5, repeat=2)
```

## Project layout

```
macro_recorder/
├── events.py      # Serializable Event / Macro data models
├── keyutils.py    # Convert pynput keys/buttons <-> strings
├── recorder.py    # MacroRecorder — captures input via pynput listeners
├── player.py      # MacroPlayer — replays events with speed/repeat control
├── storage.py     # save_macro / load_macro (JSON)
├── cli.py         # Command line interface
├── gui.py         # Tkinter GUI with global hotkeys
└── __main__.py    # `python -m macro_recorder` -> GUI
run.py             # Convenience launcher for the GUI
tests/             # Unit tests for the data + storage layer
```

## Running the tests

The data/storage layer is covered by tests that need no display:

```bash
python -m pytest            # if pytest is installed
python tests/test_events_storage.py   # or run directly
```

## Notes & tips

- **Screen coordinates are absolute.** For reliable playback, keep the same
  screen resolution and window positions as when you recorded.
- Some applications (games, elevated/admin windows) may ignore synthetic input.
  Run Python **as administrator** if a target app does not react.
- Recording mouse movement can create large files; use `--no-mouse-move` (CLI)
  or untick the checkbox (GUI) if you only need clicks and keystrokes.
- Antivirus tools sometimes flag global input hooks — this is expected for any
  macro/automation utility.

## License

Released under the MIT License. See [`LICENSE`](LICENSE).
