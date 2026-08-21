"""Persist macros to disk as JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from .events import Macro

PathLike = Union[str, Path]

# Bumped whenever the on-disk schema changes in a backwards incompatible way.
FILE_FORMAT_VERSION = 1


def save_macro(path: PathLike, macro: Macro) -> None:
    """Write ``macro`` to ``path`` as pretty printed JSON."""

    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)

    payload = {"format_version": FILE_FORMAT_VERSION, **macro.to_dict()}
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def load_macro(path: PathLike) -> Macro:
    """Read a macro previously written by :func:`save_macro`."""

    target = Path(path)
    with target.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict) or "events" not in payload:
        raise ValueError(f"{target} does not look like a macro file")

    return Macro.from_dict(payload)
