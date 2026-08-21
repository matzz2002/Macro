"""JSON storage for macro recordings."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Macro


def load_macro(path: str | Path) -> Macro:
    macro_path = Path(path)
    with macro_path.open("r", encoding="utf-8") as macro_file:
        raw = json.load(macro_file)
    if not isinstance(raw, dict):
        raise ValueError("macro file must contain a JSON object")
    return Macro.from_dict(raw)


def save_macro(macro: Macro, path: str | Path) -> None:
    macro_path = Path(path)
    macro_path.parent.mkdir(parents=True, exist_ok=True)
    with macro_path.open("w", encoding="utf-8") as macro_file:
        json.dump(macro.to_dict(), macro_file, indent=2)
        macro_file.write("\n")
