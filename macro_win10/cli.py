"""Command-line interface for the macro recorder."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .playback import play_macro
from .recorder import RecorderSession
from .storage import load_macro, save_macro


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="win10-macro",
        description="Record and replay Windows 10 keyboard and mouse macros.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record_parser = subparsers.add_parser("record", help="record a macro to JSON")
    record_parser.add_argument("output", type=Path, help="macro JSON file to write")
    record_parser.add_argument("--name", default="Recorded Macro", help="macro name")
    record_parser.add_argument(
        "--stop-key",
        default="f8",
        help="key that stops recording (default: f8)",
    )

    play_parser = subparsers.add_parser("play", help="play a saved macro")
    play_parser.add_argument("macro", type=Path, help="macro JSON file to play")
    play_parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="playback speed multiplier (default: 1.0)",
    )
    play_parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="number of playback repeats (default: 1)",
    )
    play_parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="seconds to wait before playback starts (default: 3)",
    )

    inspect_parser = subparsers.add_parser("inspect", help="show macro details")
    inspect_parser.add_argument("macro", type=Path, help="macro JSON file to inspect")

    subparsers.add_parser("gui", help="start the graphical interface")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "gui":
        from .gui import main as gui_main

        gui_main()
        return 0
    if args.command == "record":
        return _record(args.output, name=args.name, stop_key=args.stop_key)
    if args.command == "play":
        macro = load_macro(args.macro)
        print(
            f"Playing {len(macro.events)} events after {args.delay:.1f}s delay. "
            "Move mouse to the top-left corner to abort."
        )
        play_macro(
            macro,
            speed=args.speed,
            repeat=args.repeat,
            start_delay=args.delay,
        )
        return 0
    if args.command == "inspect":
        macro = load_macro(args.macro)
        print(f"Name: {macro.name}")
        print(f"Created: {macro.created_at}")
        print(f"Events: {len(macro.events)}")
        print(f"Duration: {macro.duration:.3f} seconds")
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


def _record(output: Path, *, name: str, stop_key: str) -> int:
    print(f"Recording. Press {stop_key.upper()} to stop.")
    session = RecorderSession(name=name, stop_key=stop_key)
    try:
        session.start()
        while session.is_recording:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping recording...")
    finally:
        macro = session.stop()

    save_macro(macro, output)
    print(
        f"Saved {len(macro.events)} events "
        f"({macro.duration:.3f}s) to {output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
