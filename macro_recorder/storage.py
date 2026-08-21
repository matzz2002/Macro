"""Load and save :class:`~macro_recorder.events.Macro` objects as JSON files."""

from __future__ import annotations

import json
import os
from typing import Union

from .events import Macro

PathLike = Union[str, os.PathLike]


def save_macro(macro: Macro, path: PathLike) -> None:
    """Serialize ``macro`` to ``path`` as pretty-printed JSON (UTF-8)."""

    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(macro.to_dict(), handle, indent=2, ensure_ascii=False)


def load_macro(path: PathLike) -> Macro:
    """Load a macro previously written with :func:`save_macro`."""

    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return Macro.from_dict(data)
