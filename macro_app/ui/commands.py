from __future__ import annotations

from PySide6.QtGui import QUndoCommand

from macro_app.models import MacroAction


class ActionSnapshotCommand(QUndoCommand):
    def __init__(self, label: str, apply_callback, before: list[MacroAction], after: list[MacroAction]) -> None:
        super().__init__(label)
        self.apply_callback = apply_callback
        self.before = [action.clone() for action in before]
        self.after = [action.clone() for action in after]

    def redo(self) -> None:
        self.apply_callback([action.clone() for action in self.after])

    def undo(self) -> None:
        self.apply_callback([action.clone() for action in self.before])
