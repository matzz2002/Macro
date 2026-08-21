# MacroForge - Windows 10 Keyboard and Mouse Macro Studio

MacroForge is a local desktop application for creating, recording, editing and
playing keyboard and mouse macros on Windows 10. It includes profiles, global
hotkeys, a panic key, macro import/export, autosave, tray support and a modern
dark interface.

The repository also keeps the smaller `macro.py` CLI macro player as an extra
tool, but the full desktop application starts from `run_app.py`.

## Project architecture

```text
macro_app/
  app.py                 PySide6 application entry point
  models.py              profiles, macros, actions, settings dataclasses
  storage.py             local JSON storage plus import/export
  validation.py          hotkey parsing, validation and conflict detection
  hotkeys.py             global keyboard/mouse hotkey listener
  recorder.py            explicit keyboard/mouse recorder
  player.py              threaded macro playback engine
  settings_manager.py    Windows startup integration
  action_tools.py        labels, defaults and batch delay editing
  ui/
    main_window.py       full desktop GUI, tray, profiles and action editor
    commands.py          undo/redo commands for action edits
    theme.py             light and dark styles
run_app.py               desktop launcher
macro.py                 standalone CLI macro player
requirements.txt         runtime/build dependencies
build_exe.bat            Windows EXE build helper
```

## Requirements

- Windows 10
- Python 3.9 or newer
- Dependencies from `requirements.txt`

Global input recording/playback is intended for Windows. Logic tests and the
CLI `--dry-run` mode can run on other platforms.

## Run the desktop application

1. Install Python for Windows and make sure `python` or `py -3` works in
   PowerShell.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

   If your system uses the Windows launcher:

   ```powershell
   py -3 -m pip install -r requirements.txt
   ```

3. Start the app:

   ```powershell
   python run_app.py
   ```

   or:

   ```powershell
   py -3 run_app.py
   ```

## Desktop app workflow

1. Select or create a profile in the left panel.
2. Create a macro with **+ Nowe makro**.
3. Enter a macro name, color, icon text and global hotkey.
4. Choose the run mode:
   - `Wykonaj raz`
   - `Powtórz N razy`
   - `Powtarzaj do skrótu`
   - `Powtarzaj podczas trzymania`
5. Click **Nagrywaj** to capture keyboard and mouse input. Enable
   **Nagrywaj ruchy myszy** if mouse movement should be stored too.
6. Click **Zatrzymaj nagrywanie** to finish. Actions appear in the timeline.
7. Edit actions in the center list or the right properties panel.
8. Use **Odtwórz** to run the macro and **Zatrzymaj** or the panic key to stop.
9. Changes are saved automatically to the user data folder.

The default panic key is `F12`. You can change it in the top toolbar.

## Supported desktop features

- Profiles: create, rename, duplicate, delete, import and export.
- Macros: create, duplicate, delete, search, sort, import and export.
- Global hotkeys: function keys, combinations like `Ctrl+Shift+X`, `Alt+F1`,
  and `Mouse Button 4` / `Mouse Button 5`.
- Recorder: key down/up, mouse clicks, optional mouse moves and action delays.
- Editor: add, edit, delete, copy, move and drag actions.
- Undo/redo for action-list changes.
- Delay editing in milliseconds, random delay ranges and batch delay scaling.
- Loop action with editable nested JSON action body.
- Tray icon: restore UI, stop macros or quit fully.
- Startup with Windows through the current user's Run registry key.
- Dark mode by default plus light mode.

## Build a Windows EXE

On Windows, run:

```powershell
build_exe.bat
```

The executable will be created under:

```text
dist\MacroForge\MacroForge.exe
```

You can also run PyInstaller manually:

```powershell
python -m PyInstaller --noconfirm --windowed --name MacroForge run_app.py
```

## Quick start

1. Open PowerShell or Command Prompt in this folder.
2. Preview the example macros:

   ```powershell
   python macro.py macros.example.json --list --dry-run
   python macro.py macros.example.json --macro open_notepad_and_type --dry-run --delay 0
   ```

3. Run a macro on Windows:

   ```powershell
   python macro.py macros.example.json --macro open_notepad_and_type
   ```

Playback starts after a short delay so you can put focus on the target window.
Press `Esc` to stop playback while a macro is running.

## Step-by-step: implement your own macro

Use this workflow when you want to create a new keyboard and mouse macro.

1. **Decide what the macro should do.**

   Write the manual steps first. For example:

   - Open the Windows Run dialog.
   - Type `notepad`.
   - Press `Enter`.
   - Wait for Notepad to open.
   - Type a message.

2. **Copy the example macro file.**

   ```powershell
   copy macros.example.json my-macros.json
   ```

3. **Add a new macro name under `macros`.**

   A macro is a list of actions. This example opens Calculator:

   ```json
   {
     "version": 1,
     "macros": {
       "open_calculator": [
         { "type": "hotkey", "keys": ["win", "r"] },
         { "type": "type", "text": "calc" },
         { "type": "press", "key": "enter" }
       ]
     }
   }
   ```

4. **Choose the correct action for each step.**

   - Use `hotkey` for shortcuts such as `ctrl+c`, `alt+tab`, or `win+r`.
   - Use `type` for normal text.
   - Use `press` for one key such as `enter`, `tab`, or `esc`.
   - Use `wait` when an app needs time to open or update.
   - Use `mouse_move`, `mouse_click`, and `mouse_scroll` for mouse actions.

5. **Use screen coordinates for mouse actions.**

   Mouse coordinates are pixels measured from the top-left corner of the main
   screen. Example:

   ```json
   { "type": "mouse_click", "button": "left", "x": 500, "y": 300 }
   ```

   If a click misses, adjust `x`, `y`, or add a `wait` before the click.

6. **Check that the macro file is valid.**

   ```powershell
   python macro.py my-macros.json --list --dry-run
   ```

   If your Windows Python command is `py`, use:

   ```powershell
   py -3 macro.py my-macros.json --list --dry-run
   ```

7. **Preview the macro without controlling your computer.**

   ```powershell
   python macro.py my-macros.json --macro open_calculator --dry-run --delay 0
   ```

   Confirm that the printed actions match the exact order you want.

8. **Run the macro on Windows 10.**

   Close sensitive windows first, then run:

   ```powershell
   python macro.py my-macros.json --macro open_calculator --delay 3
   ```

   After pressing `Enter`, put focus on the window where the macro should run.
   Press `Esc` to stop playback.

9. **Tune timing and coordinates.**

   If actions happen too early, add or increase `wait` actions. If mouse clicks
   land in the wrong place, adjust the coordinates and test again with
   `--dry-run` before replaying.

## Macro file format

Macro files contain a top-level `macros` object. Each macro is a list of
actions:

```json
{
  "version": 1,
  "macros": {
    "example": [
      { "type": "hotkey", "keys": ["ctrl", "l"] },
      { "type": "type", "text": "https://example.com" },
      { "type": "press", "key": "enter" },
      { "type": "wait", "seconds": 1 },
      { "type": "mouse_click", "button": "left", "x": 500, "y": 300 }
    ]
  }
}
```

Supported action types:

| Action | Required fields | Optional fields |
| --- | --- | --- |
| `wait` | `seconds` | |
| `key` | `key`, `event` (`down` or `up`) | |
| `press` | `key` | `times`, `interval` |
| `hotkey` | `keys` | |
| `type` | `text` | `interval` |
| `mouse_move` | `x`, `y` | `duration` |
| `mouse_click` | | `button`, `x`, `y`, `clicks`, `interval` |
| `mouse_scroll` | `amount` | |

Supported mouse buttons are `left`, `right`, and `middle`. Positive scroll
amounts scroll up; negative amounts scroll down.

Supported keys include letters (`a` through `z`), numbers (`0` through `9`),
function keys (`f1` through `f12`), and common names such as `enter`, `tab`,
`space`, `ctrl`, `alt`, `shift`, `win`, `esc`, arrow keys, `home`, `end`,
`delete`, `insert`, `pageup`, and `pagedown`.

## Command line options

```text
python macro.py MACRO_FILE [--macro NAME] [--list] [--dry-run] [--repeat N] [--delay SECONDS]
```

- `--macro NAME`: choose which macro to run. If omitted, the first macro in the
  file runs.
- `--list`: list macro names and exit.
- `--dry-run`: print actions without controlling the computer.
- `--repeat N`: run the selected macro more than once.
- `--delay SECONDS`: wait before playback starts. Defaults to 3 seconds.

## Testing

Run the repository tests with:

```powershell
python -m unittest
```

On systems where the command is `python3`, run:

```powershell
python3 -m unittest
```