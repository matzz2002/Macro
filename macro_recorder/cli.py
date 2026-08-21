"""Command line interface for recording and replaying macros.

Examples
--------
Record until ``F9`` (or Ctrl+C) is pressed and save to a file::

    python -m macro_recorder record my_macro.json

Play a saved macro three times at double speed::

    python -m macro_recorder play my_macro.json --repeat 3 --speed 2

Show information about a saved macro::

    python -m macro_recorder info my_macro.json
"""

from __future__ import annotations

import argparse
import sys
import threading
import time

from . import __version__
from .events import summarize
from .player import Player
from .recorder import Recorder
from .storage import load_macro, save_macro


def _cmd_record(args: argparse.Namespace) -> int:
    recorder = Recorder(capture_mouse_move=not args.no_mouse_move)

    stop_event = threading.Event()

    # Optionally bind a global hotkey to stop recording.
    hotkey_listener = None
    if args.stop_key:
        try:
            from pynput import keyboard

            hotkey_listener = keyboard.GlobalHotKeys(
                {args.stop_key: stop_event.set}
            )
            hotkey_listener.start()
        except Exception as exc:  # pragma: no cover - environment dependent
            print(f"Could not bind stop hotkey {args.stop_key!r}: {exc}", file=sys.stderr)

    print("Recording started.")
    if args.stop_key:
        print(f"Press {args.stop_key} to stop (or Ctrl+C in this terminal).")
    else:
        print("Press Ctrl+C in this terminal to stop.")

    recorder.start(name=args.name or "Recorded macro")
    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        macro = recorder.stop()
        if hotkey_listener is not None:
            hotkey_listener.stop()

    save_macro(macro, args.path)
    print(f"Saved {summarize(macro)} -> {args.path}")
    return 0


def _cmd_play(args: argparse.Namespace) -> int:
    macro = load_macro(args.path)
    print(f"Playing {summarize(macro)}")
    if args.countdown > 0:
        for remaining in range(args.countdown, 0, -1):
            print(f"Starting in {remaining}...", end="\r", flush=True)
            time.sleep(1)
        print(" " * 24, end="\r")

    player = Player(speed=args.speed)
    try:
        player.play(macro, repeat=args.repeat, blocking=True)
    except KeyboardInterrupt:
        player.stop()
        player.wait()
        print("\nPlayback interrupted.")
        return 130
    print("Playback finished.")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    macro = load_macro(args.path)
    print(summarize(macro))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macro_recorder",
        description="Record and replay keyboard & mouse macros.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_record = sub.add_parser("record", help="Record a new macro to a file.")
    p_record.add_argument("path", help="Where to save the recorded macro (.json).")
    p_record.add_argument("--name", help="Human-readable name for the macro.")
    p_record.add_argument(
        "--no-mouse-move",
        action="store_true",
        help="Do not record mouse movement (clicks/scroll only).",
    )
    p_record.add_argument(
        "--stop-key",
        default="<f9>",
        help="Global hotkey to stop recording (pynput syntax, default <f9>).",
    )
    p_record.set_defaults(func=_cmd_record)

    p_play = sub.add_parser("play", help="Replay a saved macro.")
    p_play.add_argument("path", help="Path to the macro (.json) to replay.")
    p_play.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of repetitions (0 = loop forever, Ctrl+C to stop).",
    )
    p_play.add_argument(
        "--speed", type=float, default=1.0, help="Playback speed multiplier."
    )
    p_play.add_argument(
        "--countdown",
        type=int,
        default=3,
        help="Seconds to wait before playback begins (default 3).",
    )
    p_play.set_defaults(func=_cmd_play)

    p_info = sub.add_parser("info", help="Show a summary of a saved macro.")
    p_info.add_argument("path", help="Path to the macro (.json).")
    p_info.set_defaults(func=_cmd_info)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
