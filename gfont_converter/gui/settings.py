"""Запоминание настроек: %APPDATA%\\GfontConverter\\settings.json (на Linux ~/.config)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

APP_NAME = "GfontConverter"


def settings_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME


def settings_path() -> Path:
    return settings_dir() / "settings.json"


DEFAULTS: Dict[str, Any] = {
    "params": {},
    "params_version": 0,
    "last_font": "",
    "last_font_dir": "",
    "last_save_dir": "",
    "template": "",            # пусто = встроенный шаблон
    "preview_text": "",
    "pen_width": 9.0,
    "show_guides": True,
    "show_source": False,
    "variants_n": 3,
    "log_open": True,
    "geometry": "",
}


class AppSettings:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else settings_path()
        self.data: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.data.update(raw)
        except (OSError, ValueError):
            pass  # первый запуск или испорченный файл — берём значения по умолчанию

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass  # настройки — не критично

    def __getitem__(self, key: str) -> Any:
        return self.data.get(key, DEFAULTS.get(key))

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value
