"""A small Tkinter GUI for recording and replaying keyboard/mouse macros.

The window offers Record / Stop / Play controls, playback speed and repeat
options, a live event log, and Save / Load buttons.  Global hotkeys (F9 to
toggle recording, F10 to toggle playback) work even when the window is not
focused, which is important because you usually record/play into *another*
application.

Run it with::

    python -m macro_recorder
    # or
    python -m macro_recorder gui
"""

from __future__ import annotations

import queue
import threading
from typing import Optional

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception as exc:  # pragma: no cover - headless environments
    tk = None  # type: ignore
    _TK_IMPORT_ERROR = exc
else:
    _TK_IMPORT_ERROR = None

from .events import Macro, summarize
from .hotkeys import HotkeyManager
from .player import Player
from .recorder import Recorder
from .storage import load_macro, save_macro

RECORD_HOTKEY = "<f9>"
PLAY_HOTKEY = "<f10>"


class MacroApp:
    """Tkinter application wrapping the recorder and player."""

    def __init__(self, root: "tk.Tk") -> None:
        self.root = root
        self.root.title("Macro Recorder - Keyboard & Mouse")
        self.root.geometry("560x520")
        self.root.minsize(480, 420)

        self.recorder = Recorder(on_event=self._on_recorded_event)
        self.player: Optional[Player] = None
        self.macro = Macro()

        # Cross-thread UI updates are marshalled through this queue and drained
        # on the Tk main loop via ``after``.
        self._ui_queue: "queue.Queue[callable]" = queue.Queue()

        self._build_widgets()
        self._setup_hotkeys()
        self._poll_ui_queue()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    # Widget construction
    # ------------------------------------------------------------------ #
    def _build_widgets(self) -> None:
        pad = {"padx": 6, "pady": 6}

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # -- Control buttons --------------------------------------------- #
        controls = ttk.Frame(main)
        controls.pack(fill="x")

        self.record_btn = ttk.Button(
            controls, text="\u25CF Record (F9)", command=self.toggle_record
        )
        self.record_btn.grid(row=0, column=0, **pad)

        self.play_btn = ttk.Button(
            controls, text="\u25B6 Play (F10)", command=self.toggle_play
        )
        self.play_btn.grid(row=0, column=1, **pad)

        self.clear_btn = ttk.Button(controls, text="Clear", command=self.clear_macro)
        self.clear_btn.grid(row=0, column=2, **pad)

        # -- Options ----------------------------------------------------- #
        options = ttk.LabelFrame(main, text="Playback options", padding=8)
        options.pack(fill="x", pady=(8, 0))

        ttk.Label(options, text="Repeat:").grid(row=0, column=0, sticky="w", **pad)
        self.repeat_var = tk.StringVar(value="1")
        ttk.Spinbox(
            options, from_=0, to=100000, width=8, textvariable=self.repeat_var
        ).grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(options, text="(0 = loop forever)").grid(
            row=0, column=2, sticky="w", **pad
        )

        ttk.Label(options, text="Speed:").grid(row=1, column=0, sticky="w", **pad)
        self.speed_var = tk.StringVar(value="1.0")
        ttk.Spinbox(
            options,
            from_=0.1,
            to=20.0,
            increment=0.1,
            width=8,
            textvariable=self.speed_var,
        ).grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(options, text="x").grid(row=1, column=2, sticky="w")

        self.capture_move_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options,
            text="Record mouse movement",
            variable=self.capture_move_var,
        ).grid(row=2, column=0, columnspan=3, sticky="w", **pad)

        # -- File buttons ------------------------------------------------ #
        files = ttk.Frame(main)
        files.pack(fill="x", pady=(8, 0))
        ttk.Button(files, text="Save...", command=self.save_macro).grid(
            row=0, column=0, **pad
        )
        ttk.Button(files, text="Load...", command=self.load_macro).grid(
            row=0, column=1, **pad
        )

        # -- Event log --------------------------------------------------- #
        log_frame = ttk.LabelFrame(main, text="Events", padding=8)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.log = tk.Text(log_frame, height=10, state="disabled", wrap="none")
        self.log.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        scroll.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scroll.set)

        # -- Status bar -------------------------------------------------- #
        self.status_var = tk.StringVar(value="Ready. Press F9 to record.")
        status = ttk.Label(
            self.root, textvariable=self.status_var, relief="sunken", anchor="w"
        )
        status.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------ #
    # Hotkeys
    # ------------------------------------------------------------------ #
    def _setup_hotkeys(self) -> None:
        self.hotkeys = HotkeyManager()
        # Hotkey callbacks fire on the pynput thread; marshal onto the UI queue.
        self.hotkeys.register(
            RECORD_HOTKEY, lambda: self._ui_queue.put(self.toggle_record)
        )
        self.hotkeys.register(
            PLAY_HOTKEY, lambda: self._ui_queue.put(self.toggle_play)
        )
        try:
            self.hotkeys.start()
        except Exception as exc:  # pragma: no cover - environment dependent
            self._set_status(f"Global hotkeys unavailable: {exc}")

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #
    def toggle_record(self) -> None:
        if self.recorder.is_recording:
            self.stop_record()
        else:
            self.start_record()

    def start_record(self) -> None:
        if self.player is not None and self.player.is_playing:
            self._set_status("Cannot record while playing.")
            return
        self.recorder.capture_mouse_move = self.capture_move_var.get()
        self._clear_log()
        self.recorder.start()
        self.record_btn.config(text="\u25A0 Stop (F9)")
        self._set_status("Recording... press F9 to stop.")

    def stop_record(self) -> None:
        self.macro = self.recorder.stop()
        self.record_btn.config(text="\u25CF Record (F9)")
        self._set_status(f"Recorded {summarize(self.macro)}")

    # ------------------------------------------------------------------ #
    # Playback
    # ------------------------------------------------------------------ #
    def toggle_play(self) -> None:
        if self.player is not None and self.player.is_playing:
            self.stop_play()
        else:
            self.start_play()

    def start_play(self) -> None:
        if self.recorder.is_recording:
            self._set_status("Cannot play while recording.")
            return
        if len(self.macro) == 0:
            self._set_status("Nothing to play. Record or load a macro first.")
            return

        try:
            repeat = int(self.repeat_var.get())
        except ValueError:
            repeat = 1
        try:
            speed = float(self.speed_var.get())
            if speed <= 0:
                speed = 1.0
        except ValueError:
            speed = 1.0

        self.player = Player(
            speed=speed,
            on_progress=self._on_progress,
            on_finish=lambda: self._ui_queue.put(self._on_play_finished),
        )
        self.play_btn.config(text="\u25A0 Stop (F10)")
        self._set_status("Playing...")
        self.player.play(self.macro, repeat=repeat)

    def stop_play(self) -> None:
        if self.player is not None:
            self.player.stop()
        self._set_status("Stopping playback...")

    def _on_play_finished(self) -> None:
        self.play_btn.config(text="\u25B6 Play (F10)")
        self._set_status("Playback finished.")

    def _on_progress(self, index: int, total: int) -> None:
        self._ui_queue.put(lambda: self._set_status(f"Playing event {index}/{total}"))

    # ------------------------------------------------------------------ #
    # File operations
    # ------------------------------------------------------------------ #
    def save_macro(self) -> None:
        if len(self.macro) == 0:
            self._set_status("Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")],
            title="Save macro",
        )
        if not path:
            return
        save_macro(self.macro, path)
        self._set_status(f"Saved to {path}")

    def load_macro(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")],
            title="Load macro",
        )
        if not path:
            return
        try:
            self.macro = load_macro(path)
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            return
        self._clear_log()
        self._append_log(f"Loaded {summarize(self.macro)}")
        self._set_status(f"Loaded {len(self.macro)} events from {path}")

    def clear_macro(self) -> None:
        if self.recorder.is_recording:
            return
        self.macro = Macro()
        self._clear_log()
        self._set_status("Cleared.")

    # ------------------------------------------------------------------ #
    # Live event log (called from recorder thread)
    # ------------------------------------------------------------------ #
    def _on_recorded_event(self, event) -> None:
        text = self._format_event(event)
        self._ui_queue.put(lambda: self._append_log(text))

    @staticmethod
    def _format_event(event) -> str:
        etype = event.type
        if etype == "key":
            action = "down" if event.pressed else "up"
            return f"[{event.time:6.2f}s] key {event.key} {action}"
        if etype == "mouse_move":
            return f"[{event.time:6.2f}s] move -> ({event.x}, {event.y})"
        if etype == "mouse_click":
            action = "down" if event.pressed else "up"
            return f"[{event.time:6.2f}s] {event.button} {action} @ ({event.x}, {event.y})"
        if etype == "mouse_scroll":
            return f"[{event.time:6.2f}s] scroll ({event.dx}, {event.dy}) @ ({event.x}, {event.y})"
        return f"[{event.time:6.2f}s] {etype}"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _append_log(self, text: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self) -> None:
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                callback = self._ui_queue.get_nowait()
                try:
                    callback()
                except Exception:
                    pass
        except queue.Empty:
            pass
        self.root.after(30, self._poll_ui_queue)

    def _on_close(self) -> None:
        try:
            if self.recorder.is_recording:
                self.recorder.stop()
            if self.player is not None and self.player.is_playing:
                self.player.stop()
            self.hotkeys.stop()
        finally:
            self.root.destroy()


def run() -> int:
    """Launch the GUI.  Returns a process exit code."""

    if tk is None:  # pragma: no cover - headless environments
        print(
            "Tkinter is not available in this Python installation: "
            f"{_TK_IMPORT_ERROR}"
        )
        return 1

    root = tk.Tk()
    MacroApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
