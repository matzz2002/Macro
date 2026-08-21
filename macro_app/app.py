from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .storage import JsonStorage
from .ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv or sys.argv)
    app.setApplicationName("MacroForge")
    app.setOrganizationName("MacroForge")
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow(JsonStorage())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
