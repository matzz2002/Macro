# Windows 10 Keyboard and Mouse Macro Player

This repository contains a small Python program for replaying keyboard and
mouse macros on Windows 10. Macros are written in JSON and executed with the
native Windows `SendInput` API, so no third-party packages are required.

## Requirements

- Windows 10
- Python 3.9 or newer

Real macro playback only works on Windows. The `--dry-run` option works on any
platform and prints what would happen without controlling the keyboard or mouse.

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