"""Tkinter GUI for the Windows 10 macro recorder."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .models import Macro, MacroEvent
from .playback import play_macro
from .recorder import RecorderSession
from .storage import load_macro, save_macro


class MacroApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Windows 10 Keyboard and Mouse Macro")
        self.root.geometry("720x460")

        self.current_macro = Macro()
        self.session: RecorderSession | None = None
        self.current_path: str | None = None

        self.name_var = tk.StringVar(value=self.current_macro.name)
        self.status_var = tk.StringVar(value="Ready")
        self.file_var = tk.StringVar(value="No file loaded")
        self.summary_var = tk.StringVar(value="0 events, 0.000 seconds")

        self._build_ui()
        self._refresh_summary()

    def _build_ui(self) -> None:
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill=tk.BOTH, expand=True)

        name_frame = ttk.Frame(root_frame)
        name_frame.pack(fill=tk.X)
        ttk.Label(name_frame, text="Macro name:").pack(side=tk.LEFT)
        ttk.Entry(name_frame, textvariable=self.name_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0)
        )

        button_frame = ttk.Frame(root_frame)
        button_frame.pack(fill=tk.X, pady=12)
        self.record_button = ttk.Button(
            button_frame,
            text="Start Recording",
            command=self.start_recording,
        )
        self.record_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(
            button_frame,
            text="Stop (F8)",
            command=self.stop_recording,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_frame, text="Play", command=self.play_current_macro).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(button_frame, text="Load", command=self.load_macro_file).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(button_frame, text="Save", command=self.save_macro_file).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(button_frame, text="Save As", command=self.save_macro_file_as).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        ttk.Label(root_frame, textvariable=self.file_var).pack(anchor=tk.W)
        ttk.Label(root_frame, textvariable=self.summary_var).pack(anchor=tk.W)

        event_frame = ttk.LabelFrame(root_frame, text="Recorded events")
        event_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.event_list = tk.Listbox(event_frame, height=12)
        scrollbar = ttk.Scrollbar(
            event_frame,
            orient=tk.VERTICAL,
            command=self.event_list.yview,
        )
        self.event_list.configure(yscrollcommand=scrollbar.set)
        self.event_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(root_frame, textvariable=self.status_var).pack(anchor=tk.W, pady=(8, 0))

    def start_recording(self) -> None:
        if self.session and self.session.is_recording:
            return

        self.current_path = None
        self.current_macro = Macro(name=self.name_var.get() or "Recorded Macro")
        self.event_list.delete(0, tk.END)
        self.session = RecorderSession(
            name=self.current_macro.name,
            stop_key="f8",
            on_event=self._recorded_event,
        )

        try:
            self.session.start()
        except Exception as exc:
            messagebox.showerror("Cannot start recording", str(exc))
            self.status_var.set("Recording failed")
            return

        self.record_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.status_var.set("Recording... press F8 or click Stop to finish")
        self.root.after(250, self._poll_recording)

    def stop_recording(self) -> None:
        if not self.session:
            return

        self.current_macro = self.session.stop()
        self.name_var.set(self.current_macro.name)
        self.record_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_var.set("Recording stopped")
        self._refresh_summary()

    def play_current_macro(self) -> None:
        if not self.current_macro.events:
            messagebox.showinfo("No macro", "Record or load a macro before playing.")
            return

        speed = simpledialog.askfloat(
            "Playback speed",
            "Speed multiplier:",
            initialvalue=1.0,
            minvalue=0.1,
        )
        if speed is None:
            return
        repeat = simpledialog.askinteger(
            "Repeat",
            "Number of times to play:",
            initialvalue=1,
            minvalue=1,
        )
        if repeat is None:
            return

        self.status_var.set(
            "Playback starts in 3 seconds. Move mouse to top-left to abort."
        )
        thread = threading.Thread(
            target=self._play_macro_worker,
            args=(speed, repeat),
            daemon=True,
        )
        thread.start()

    def load_macro_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Load macro",
            filetypes=[("Macro JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            self.current_macro = load_macro(path)
        except Exception as exc:
            messagebox.showerror("Cannot load macro", str(exc))
            return

        self.current_path = path
        self.name_var.set(self.current_macro.name)
        self.file_var.set(path)
        self._render_events()
        self._refresh_summary()
        self.status_var.set("Macro loaded")

    def save_macro_file(self) -> None:
        if self.current_path:
            self._save_to_path(self.current_path)
        else:
            self.save_macro_file_as()

    def save_macro_file_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save macro",
            defaultextension=".json",
            filetypes=[("Macro JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._save_to_path(path)

    def _save_to_path(self, path: str) -> None:
        self.current_macro.name = self.name_var.get() or "Recorded Macro"
        try:
            save_macro(self.current_macro, path)
        except Exception as exc:
            messagebox.showerror("Cannot save macro", str(exc))
            return

        self.current_path = path
        self.file_var.set(path)
        self.status_var.set("Macro saved")

    def _recorded_event(self, event: MacroEvent) -> None:
        self.root.after(0, self._append_event, event)

    def _append_event(self, event: MacroEvent) -> None:
        self.event_list.insert(tk.END, self._format_event(event))
        self.event_list.yview_moveto(1.0)
        self._refresh_summary()

    def _render_events(self) -> None:
        self.event_list.delete(0, tk.END)
        for event in self.current_macro.events:
            self.event_list.insert(tk.END, self._format_event(event))

    def _refresh_summary(self) -> None:
        macro = self.session.macro() if self.session and self.session.is_recording else self.current_macro
        self.summary_var.set(
            f"{len(macro.events)} events, {macro.duration:.3f} seconds"
        )

    def _poll_recording(self) -> None:
        if not self.session:
            return
        if not self.session.is_recording:
            self.stop_recording()
            return
        self._refresh_summary()
        self.root.after(250, self._poll_recording)

    def _play_macro_worker(self, speed: float, repeat: int) -> None:
        try:
            play_macro(self.current_macro, speed=speed, repeat=repeat, start_delay=3)
        except Exception as exc:
            self.root.after(0, self._playback_failed, exc)
        else:
            self.root.after(0, lambda: self.status_var.set("Playback finished"))

    def _playback_failed(self, exc: Exception) -> None:
        messagebox.showerror("Playback stopped", str(exc))
        self.status_var.set("Playback stopped")

    @staticmethod
    def _format_event(event: MacroEvent) -> str:
        return f"{event.time:8.3f}s  {event.type:<13} {event.data}"


def main() -> None:
    root = tk.Tk()
    MacroApp(root)
    root.mainloop()
