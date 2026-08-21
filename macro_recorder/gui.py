"""A small Tkinter GUI for recording, saving, loading and playing macros.

Global hotkeys (they work even when the window is not focused, which is what you
want for a macro tool):

    F9  -> start recording
    F10 -> stop recording / stop playback
    F11 -> play the current macro
"""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from . import __version__
from .events import Macro
from .player import MacroPlayer
from .recorder import MacroRecorder
from .storage import load_macro, save_macro

HOTKEY_HELP = "F9 Record   |   F10 Stop   |   F11 Play"


class MacroApp:
    """The application window and all of its wiring."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Macro Recorder {__version__}")
        self.root.geometry("460x430")
        self.root.minsize(420, 400)

        self.recorder: Optional[MacroRecorder] = None
        self.player = MacroPlayer()
        self.macro: Optional[Macro] = None

        # Listener callbacks fire on background threads; funnel their work back
        # onto the Tk main loop through this queue which we poll periodically.
        self._ui_queue: "queue.Queue[callable]" = queue.Queue()

        self._build_widgets()
        self._install_hotkeys()

        self.root.after(50, self._drain_ui_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------- widgets
    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 6}

        header = ttk.Label(
            self.root, text="Keyboard & Mouse Macro", font=("Segoe UI", 14, "bold")
        )
        header.pack(**pad)

        # Options -----------------------------------------------------------
        options = ttk.LabelFrame(self.root, text="Options")
        options.pack(fill="x", **pad)

        self.capture_move_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options,
            text="Record mouse movement",
            variable=self.capture_move_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=4)

        ttk.Label(options, text="Speed:").grid(row=1, column=0, sticky="w", padx=6)
        self.speed_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(
            options,
            from_=0.1,
            to=10.0,
            increment=0.1,
            width=6,
            textvariable=self.speed_var,
        ).grid(row=1, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(options, text="Repeat (0 = loop):").grid(
            row=2, column=0, sticky="w", padx=6
        )
        self.repeat_var = tk.IntVar(value=1)
        ttk.Spinbox(
            options,
            from_=0,
            to=9999,
            width=6,
            textvariable=self.repeat_var,
        ).grid(row=2, column=1, sticky="w", padx=6, pady=4)

        # Transport buttons -------------------------------------------------
        buttons = ttk.Frame(self.root)
        buttons.pack(fill="x", **pad)

        self.record_btn = ttk.Button(
            buttons, text="Record (F9)", command=self.start_recording
        )
        self.record_btn.grid(row=0, column=0, sticky="ew", padx=4)

        self.stop_btn = ttk.Button(
            buttons, text="Stop (F10)", command=self.stop, state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=4)

        self.play_btn = ttk.Button(
            buttons, text="Play (F11)", command=self.play, state="disabled"
        )
        self.play_btn.grid(row=0, column=2, sticky="ew", padx=4)

        for column in range(3):
            buttons.columnconfigure(column, weight=1)

        # File buttons ------------------------------------------------------
        files = ttk.Frame(self.root)
        files.pack(fill="x", **pad)
        self.save_btn = ttk.Button(
            files, text="Save...", command=self.save, state="disabled"
        )
        self.save_btn.grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(files, text="Load...", command=self.load).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        files.columnconfigure(0, weight=1)
        files.columnconfigure(1, weight=1)

        # Status ------------------------------------------------------------
        info = ttk.LabelFrame(self.root, text="Status")
        info.pack(fill="both", expand=True, **pad)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(info, textvariable=self.status_var, font=("Segoe UI", 10)).pack(
            anchor="w", padx=8, pady=6
        )

        self.detail_var = tk.StringVar(value="No macro loaded.")
        ttk.Label(info, textvariable=self.detail_var, foreground="#555").pack(
            anchor="w", padx=8
        )

        ttk.Label(self.root, text=HOTKEY_HELP, foreground="#777").pack(pady=(0, 8))

    # -------------------------------------------------------------- hotkeys
    def _install_hotkeys(self) -> None:
        try:
            from pynput import keyboard
        except Exception as exc:  # pragma: no cover - platform dependent
            self.status_var.set(f"Global hotkeys unavailable: {exc}")
            self._hotkeys = None
            return

        self._hotkeys = keyboard.GlobalHotKeys(
            {
                "<f9>": lambda: self._ui_queue.put(self.start_recording),
                "<f10>": lambda: self._ui_queue.put(self.stop),
                "<f11>": lambda: self._ui_queue.put(self.play),
            }
        )
        self._hotkeys.start()

    def _drain_ui_queue(self) -> None:
        try:
            while True:
                callback = self._ui_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self._drain_ui_queue)

    # --------------------------------------------------------------- actions
    def start_recording(self) -> None:
        if (self.recorder and self.recorder.is_recording) or self.player.is_playing:
            return

        self.recorder = MacroRecorder(
            capture_mouse_move=self.capture_move_var.get(),
            on_event=lambda count: self._ui_queue.put(
                lambda: self.status_var.set(f"Recording... {count} events")
            ),
        )
        self.recorder.start()
        self.status_var.set("Recording... 0 events")
        self._set_recording_ui(True)

    def stop(self) -> None:
        if self.recorder and self.recorder.is_recording:
            self.macro = self.recorder.stop()
            self._set_recording_ui(False)
            self.status_var.set("Recording stopped.")
            self._update_detail()
            self.save_btn.config(state="normal")
            self.play_btn.config(state="normal")
        elif self.player.is_playing:
            self.player.stop()
            self.status_var.set("Playback stopped.")

    def play(self) -> None:
        if self.macro is None or not self.macro.events:
            messagebox.showinfo("Nothing to play", "Record or load a macro first.")
            return
        if self.player.is_playing or (self.recorder and self.recorder.is_recording):
            return

        try:
            speed = max(0.1, float(self.speed_var.get()))
            repeat = max(0, int(self.repeat_var.get()))
        except (tk.TclError, ValueError):
            messagebox.showerror("Invalid options", "Speed/repeat must be numbers.")
            return

        self._set_playing_ui(True)
        self.status_var.set("Playing...")
        self.player.play(
            self.macro,
            speed=speed,
            repeat=repeat,
            on_progress=lambda i, total: self._ui_queue.put(
                lambda: self.status_var.set(f"Playing event {i}/{total}")
            ),
            on_done=lambda: self._ui_queue.put(self._on_play_done),
        )

    def save(self) -> None:
        if self.macro is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")],
            initialfile="macro.json",
        )
        if not path:
            return
        save_macro(path, self.macro)
        self.status_var.set(f"Saved to {path}")

    def load(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.macro = load_macro(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not load macro", str(exc))
            return
        self.status_var.set(f"Loaded {path}")
        self._update_detail()
        self.save_btn.config(state="normal")
        self.play_btn.config(state="normal")

    # ------------------------------------------------------------- ui helpers
    def _on_play_done(self) -> None:
        self._set_playing_ui(False)
        if "stopped" not in self.status_var.get().lower():
            self.status_var.set("Playback finished.")

    def _set_recording_ui(self, recording: bool) -> None:
        self.record_btn.config(state="disabled" if recording else "normal")
        self.stop_btn.config(state="normal" if recording else "disabled")
        self.play_btn.config(
            state="disabled" if recording else self.play_btn.cget("state")
        )

    def _set_playing_ui(self, playing: bool) -> None:
        self.record_btn.config(state="disabled" if playing else "normal")
        self.stop_btn.config(state="normal" if playing else "disabled")
        self.play_btn.config(state="disabled" if playing else "normal")

    def _update_detail(self) -> None:
        if self.macro is None:
            self.detail_var.set("No macro loaded.")
            return
        self.detail_var.set(
            f"{self.macro.name}\n"
            f"{len(self.macro.events)} events, {self.macro.duration:.1f}s"
        )

    def _on_close(self) -> None:
        try:
            if self.recorder and self.recorder.is_recording:
                self.recorder.stop()
            if self.player.is_playing:
                self.player.stop()
            if getattr(self, "_hotkeys", None) is not None:
                self._hotkeys.stop()
        finally:
            self.root.destroy()


def main() -> int:
    root = tk.Tk()
    MacroApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
