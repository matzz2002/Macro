"""Command line interface for the macro recorder/player.

Examples
--------
Record until you press ``Esc`` and save to a file::

    python -m macro_recorder.cli record -o macros/login.json

Play it back twice at double speed::

    python -m macro_recorder.cli play macros/login.json --speed 2 --repeat 2

Show what is inside a macro file::

    python -m macro_recorder.cli info macros/login.json
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import List, Optional

from . import __version__
from .storage import load_macro, save_macro


def _record(args: argparse.Namespace) -> int:
    # Imported lazily so `info` works on systems without a pynput backend.
    from pynput import keyboard

    from .keyutils import str_to_key
    from .recorder import MacroRecorder

    stop_key = str_to_key(args.stop_key)
    recorder = MacroRecorder(
        capture_mouse_move=not args.no_mouse_move,
        mouse_move_interval=args.move_interval,
        on_event=lambda count: print(f"\rCaptured {count} events", end="", flush=True),
    )

    print(f"Recording... press '{args.stop_key}' to stop.")
    recorder.start()

    done = {"flag": False}

    def _watch_stop(key) -> Optional[bool]:
        if key == stop_key:
            done["flag"] = True
            return False  # unsubscribe this listener
        return None

    with keyboard.Listener(on_press=_watch_stop) as listener:
        while not done["flag"]:
            time.sleep(0.05)
        listener.stop()

    macro = recorder.stop()
    macro.name = args.name or macro.name
    save_macro(args.output, macro)
    print(
        f"\nSaved {len(macro.events)} events "
        f"({macro.duration:.1f}s) to {args.output}"
    )
    return 0


def _play(args: argparse.Namespace) -> int:
    from .player import MacroPlayer

    macro = load_macro(args.file)
    if not macro.events:
        print("Macro is empty, nothing to play.")
        return 0

    if args.countdown > 0:
        for remaining in range(args.countdown, 0, -1):
            print(f"\rStarting in {remaining}...", end="", flush=True)
            time.sleep(1)
        print()

    player = MacroPlayer()

    def _progress(index: int, total: int) -> None:
        print(f"\rPlaying event {index}/{total}", end="", flush=True)

    player.play(
        macro,
        speed=args.speed,
        repeat=args.repeat,
        on_progress=_progress,
        block=True,
    )
    print("\nDone.")
    return 0


def _info(args: argparse.Namespace) -> int:
    macro = load_macro(args.file)
    print(f"Name:            {macro.name}")
    print(f"Created:         {macro.created_at}")
    print(f"App version:     {macro.app_version}")
    print(f"Captured moves:  {macro.captured_mouse_move}")
    print(f"Events:          {len(macro.events)}")
    print(f"Duration:        {macro.duration:.2f}s")

    if args.verbose:
        print("\nEvents:")
        for event in macro.events:
            print(f"  [{event.time:8.3f}s] {event.describe()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macro_recorder",
        description="Record and replay keyboard & mouse macros.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="Record a new macro.")
    record.add_argument("-o", "--output", required=True, help="Output JSON file.")
    record.add_argument("-n", "--name", help="Friendly name for the macro.")
    record.add_argument(
        "--stop-key",
        default="esc",
        help="Key that stops recording (default: esc).",
    )
    record.add_argument(
        "--no-mouse-move",
        action="store_true",
        help="Do not record mouse movement, only clicks/scroll.",
    )
    record.add_argument(
        "--move-interval",
        type=float,
        default=0.02,
        help="Minimum seconds between recorded mouse-move samples.",
    )
    record.set_defaults(func=_record)

    play = subparsers.add_parser("play", help="Play a saved macro.")
    play.add_argument("file", help="Macro JSON file to play.")
    play.add_argument(
        "-s", "--speed", type=float, default=1.0, help="Playback speed multiplier."
    )
    play.add_argument(
        "-r",
        "--repeat",
        type=int,
        default=1,
        help="Times to repeat (0 = loop forever until Ctrl+C).",
    )
    play.add_argument(
        "-c",
        "--countdown",
        type=int,
        default=3,
        help="Seconds to wait before playback starts.",
    )
    play.set_defaults(func=_play)

    info = subparsers.add_parser("info", help="Inspect a macro file.")
    info.add_argument("file", help="Macro JSON file to inspect.")
    info.add_argument(
        "-v", "--verbose", action="store_true", help="List every event."
    )
    info.set_defaults(func=_info)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
