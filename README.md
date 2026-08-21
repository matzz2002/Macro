# Windows 10 Keyboard and Mouse Macro

A small Python program for recording and replaying keyboard and mouse macros on
Windows 10. It includes:

- A Tkinter desktop GUI
- A Command Prompt / PowerShell CLI
- JSON macro files that are easy to inspect and edit
- Playback countdown and pyautogui fail-safe support

> Safety note: playback controls your real keyboard and mouse. Keep your hands
> near the mouse and move the pointer to the top-left corner of the screen to
> abort playback.

## Requirements

- Windows 10
- Python 3.10 or newer
- The packages in `requirements.txt`

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Or install the project as a local command:

```powershell
py -m pip install .
```

## Start the graphical program

From the repository folder:

```powershell
py -m macro_win10 gui
```

If installed with `py -m pip install .`, you can also run:

```powershell
win10-macro gui
```

GUI workflow:

1. Enter a macro name.
2. Click **Start Recording**.
3. Perform the keyboard and mouse actions you want to save.
4. Press **F8** or click **Stop**.
5. Click **Save As** and save the macro as a `.json` file.
6. Click **Play** to replay it. Playback starts after a 3 second delay.

## Command-line usage

Record a macro until `F8` is pressed:

```powershell
py -m macro_win10 record macros\open-notepad.json --name "Open Notepad"
```

Play a saved macro:

```powershell
py -m macro_win10 play macros\open-notepad.json
```

Play faster, repeat twice, and wait 5 seconds before starting:

```powershell
py -m macro_win10 play macros\open-notepad.json --speed 1.5 --repeat 2 --delay 5
```

Show macro details:

```powershell
py -m macro_win10 inspect macros\open-notepad.json
```

## Macro file format

Macros are saved as JSON:

```json
{
  "version": 1,
  "name": "Example",
  "created_at": "2026-08-21T00:00:00+00:00",
  "duration": 0.2,
  "events": [
    {
      "time": 0.0,
      "type": "key_down",
      "data": { "key": "a" }
    },
    {
      "time": 0.1,
      "type": "key_up",
      "data": { "key": "a" }
    }
  ]
}
```

Supported event types:

- `key_down`
- `key_up`
- `mouse_move`
- `mouse_down`
- `mouse_up`
- `mouse_scroll`

See `examples/sample_macro.json` for a complete sample.

## Development checks

The serialization tests do not require a Windows desktop session:

```powershell
py -m unittest discover -s tests
```