"""Build a standalone Windows executable with PyInstaller.

Run this on Windows 10 after installing the dev requirements::

    pip install -r requirements-dev.txt
    python build_exe.py

The resulting ``MacroRecorder.exe`` is written to the ``dist`` folder and can
be run without a Python installation.
"""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "MacroRecorder",
        "run_gui.py",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
