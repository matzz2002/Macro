"""Package entry point.

Running ``python -m macro_recorder`` with no arguments (or ``gui``) launches the
graphical interface.  Any other arguments are handed to the command line
interface, so ``python -m macro_recorder record out.json`` works as well.
"""

from __future__ import annotations

import sys


def main() -> int:
    argv = sys.argv[1:]

    # No arguments, or an explicit "gui" command -> launch the GUI.
    if not argv or argv[0] == "gui":
        from .gui import run

        return run()

    from .cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
