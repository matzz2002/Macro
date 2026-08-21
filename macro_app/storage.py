from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .models import AppData, AppSettings, Macro, Profile


APP_DIR_NAME = "MacroForge"
DATA_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"


class StorageError(RuntimeError):
    pass


def app_data_dir() -> Path:
    if os.name == "nt":
        base = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".macroforge"


class JsonStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or app_data_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.data_path = self.root / DATA_FILE
        self.settings_path = self.root / SETTINGS_FILE

    def load_data(self) -> AppData:
        if not self.data_path.exists():
            data = AppData.default()
            self.save_data(data)
            return data
        try:
            payload = json.loads(self.data_path.read_text(encoding="utf-8"))
            return AppData.from_dict(payload)
        except Exception as exc:
            backup = self.data_path.with_suffix(".broken.json")
            shutil.copy2(self.data_path, backup)
            raise StorageError(f"Nie udało się wczytać profili. Kopia uszkodzonego pliku: {backup}") from exc

    def save_data(self, data: AppData) -> None:
        self._write_json(self.data_path, data.to_dict())

    def load_settings(self) -> AppSettings:
        if not self.settings_path.exists():
            settings = AppSettings()
            self.save_settings(settings)
            return settings
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return AppSettings.from_dict(payload)
        except Exception as exc:
            backup = self.settings_path.with_suffix(".broken.json")
            shutil.copy2(self.settings_path, backup)
            raise StorageError(f"Nie udało się wczytać ustawień. Kopia uszkodzonego pliku: {backup}") from exc

    def save_settings(self, settings: AppSettings) -> None:
        self._write_json(self.settings_path, settings.to_dict())

    def export_profile(self, profile: Profile, path: Path) -> None:
        self._write_json(path, {"kind": "macroforge_profile", "profile": profile.to_dict()})

    def import_profile(self, path: Path) -> Profile:
        payload = self._read_json(path)
        if payload.get("kind") == "macroforge_profile":
            return Profile.from_dict(payload["profile"])
        if "macros" in payload:
            return Profile.from_dict(payload)
        raise StorageError("Wybrany plik nie wygląda jak eksport profilu.")

    def export_macro(self, macro: Macro, path: Path) -> None:
        self._write_json(path, {"kind": "macroforge_macro", "macro": macro.to_dict()})

    def import_macro(self, path: Path) -> Macro:
        payload = self._read_json(path)
        if payload.get("kind") == "macroforge_macro":
            macro = Macro.from_dict(payload["macro"])
            macro.hotkey = ""
            return macro
        if "actions" in payload:
            macro = Macro.from_dict(payload)
            macro.hotkey = ""
            return macro
        raise StorageError("Wybrany plik nie wygląda jak eksport makra.")

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise StorageError(f"Nie udało się wczytać pliku: {path}") from exc

    def _write_json(self, path: Path, payload: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            temporary.replace(path)
        except Exception as exc:
            raise StorageError(f"Nie udało się zapisać pliku: {path}") from exc
