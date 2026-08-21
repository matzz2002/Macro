# Macro Recorder — Keyboard & Mouse Macros for Windows 10

A lightweight program that **records and replays keyboard and mouse actions**
on Windows 10 (it also runs on macOS and Linux). Record a sequence once, then
play it back as many times as you like — great for automating repetitive tasks,
form filling, game grinding, testing, and demos.

It ships with:

- A simple **graphical interface** (Tkinter) with Record / Play / Stop buttons.
- **Global hotkeys** (`F9` record, `F10` play) that work even when the window
  is in the background — because you usually record into *another* app.
- A **command line interface** for scripting and automation.
- **Save / load** macros as human-readable JSON files.
- Adjustable **playback speed** and **repeat count** (including infinite loop).

---

## Features

| Feature | Details |
|---|---|
| Keyboard capture | Every key press/release, including modifiers and special keys. |
| Mouse capture | Movement (throttled), left/right/middle clicks, and scrolling. |
| Accurate timing | Original delays between actions are preserved on playback. |
| Speed control | Play back faster or slower with a speed multiplier. |
| Repeat | Run a macro N times, or loop forever until you stop it. |
| Portable files | Macros are plain JSON — easy to inspect, edit, and share. |
| Standalone build | Package into a single `MacroRecorder.exe` with PyInstaller. |

---

## Quick start (Windows 10)

### 1. Install Python

Install **Python 3.8 or newer** from [python.org](https://www.python.org/downloads/windows/)
and tick **“Add Python to PATH”** during installation.

### 2. Install the program

Double-click **`install.bat`** (or run it from a terminal). This installs the
required `pynput` package.

Alternatively, from a command prompt in this folder:

```bat
py -3 -m pip install -r requirements.txt
```

### 3. Run it

Double-click **`run_gui.bat`**, or run:

```bat
py -3 run_gui.py
```

---

## Using the GUI

1. Press **Record (F9)** and perform the keyboard/mouse actions you want to
   capture in any application.
2. Press **Stop (F9)** when finished.
3. Press **Play (F10)** to replay the recorded actions.
4. Optionally set **Repeat** (0 = loop forever) and **Speed** before playing.
5. Use **Save…** / **Load…** to store macros for later.

> **Tip:** `F9` and `F10` are *global* hotkeys, so you can start and stop
> recording/playback without clicking back on the window.

> **Note on permissions:** On Windows, if you want to record or control apps
> that run **as administrator** (or the login screen), run this program as
> administrator too. On macOS you must grant **Accessibility** and **Input
> Monitoring** permissions in *System Settings → Privacy & Security*.

---

## Command line usage

The same functionality is available without the GUI:

```bat
REM Record a macro; press F9 (or Ctrl+C) to stop
py -3 -m macro_recorder record my_macro.json --name "My task"

REM Replay it 3 times at 2x speed (3-second countdown first)
py -3 -m macro_recorder play my_macro.json --repeat 3 --speed 2

REM Loop forever until Ctrl+C
py -3 -m macro_recorder play my_macro.json --repeat 0

REM Show a summary of a saved macro
py -3 -m macro_recorder info my_macro.json
```

Run `py -3 -m macro_recorder record --help` (or `play --help`) for all options.

---

## Building a standalone `.exe`

To create an executable that runs without Python installed:

```bat
py -3 -m pip install -r requirements-dev.txt
py -3 build_exe.py
```

The result is `dist\MacroRecorder.exe`.

---

## Macro file format

Macros are stored as JSON. Each event records the time (seconds from the start
of the recording) at which it happened:

```json
{
  "name": "Type hello and click",
  "version": 1,
  "events": [
    { "type": "key", "time": 0.10, "key": "h", "pressed": true },
    { "type": "key", "time": 0.15, "key": "h", "pressed": false },
    { "type": "mouse_move", "time": 1.00, "x": 400, "y": 300 },
    { "type": "mouse_click", "time": 1.20, "x": 400, "y": 300,
      "button": "Button.left", "pressed": true }
  ]
}
```

Event types: `key`, `mouse_move`, `mouse_click`, `mouse_scroll`. See
[`examples/sample_macro.json`](examples/sample_macro.json) for a complete
example you can load and play.

---

## Project layout

```
macro_recorder/
  events.py     Serializable event/macro model (no third-party deps)
  recorder.py   Captures keyboard & mouse input via pynput
  player.py     Replays a macro via pynput controllers
  storage.py    JSON load/save
  hotkeys.py    Global hotkey manager
  gui.py        Tkinter user interface
  cli.py        Command line interface
  __main__.py   Entry point (GUI by default, CLI with arguments)
run_gui.py      Double-click launcher / PyInstaller entry point
build_exe.py    Builds a standalone Windows executable
tests/          Unit tests for the event model and storage
examples/       A ready-to-play sample macro
```

---

## Development

Run the unit tests (they don't require a display or `pynput`):

```bash
python -m unittest discover -s tests -v
```

---

## Troubleshooting

- **Nothing is typed/clicked on playback** — some games and secure apps block
  synthetic input; try running as administrator.
- **Global hotkeys don't work** — another program may already own `F9`/`F10`,
  or the app needs administrator rights.
- **`ModuleNotFoundError: pynput`** — run `install.bat` (or
  `pip install -r requirements.txt`).

---

## License

MIT — see [`LICENSE`](LICENSE).
