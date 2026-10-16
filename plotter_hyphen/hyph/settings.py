"""Настройки утилиты: хранятся в JSON (%APPDATA%\\PlotterHyphen\\settings.json)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Tuple

from .metrics import DEFAULT_GAP, DEFAULT_SPACE, Metrics

CALIB_TEXT = "Съешь же ещё этих мягких французских булок"
# Пока нет калибровки: примерно 0,022 мм на единицу (заглавная ≈ 7 мм у «Мой почерк»).
DEFAULT_MM_PER_UNIT = 0.022


@dataclass
class Settings:
    font_path: str = ""
    hyphenate: bool = True          # «Переносы»: выкл — слова переносятся целиком, как раньше
    line_mm: float = 180.0          # ширина строки на бумаге
    margin_pct: float = 3.0         # запас, чтобы программа плоттера не перенесла строку сама
    calib_text: str = CALIB_TEXT    # эталонная строка
    calib_mm: float = 0.0           # её длина на бумаге, мм (0 — не откалибровано)
    gap: float = DEFAULT_GAP        # межбуквенный интервал, ед. шрифта
    space: float = DEFAULT_SPACE    # ширина пробела, ед. шрифта

    def mm_per_unit(self, metrics: Metrics) -> Tuple[float, bool]:
        """(мм на единицу шрифта, откалибровано ли)."""
        units = metrics.text_width(self.calib_text) if self.calib_text.strip() else 0.0
        if self.calib_mm > 0 and units > 0:
            return self.calib_mm / units, True
        return DEFAULT_MM_PER_UNIT, False

    def max_units(self, metrics: Metrics) -> float:
        """Допустимая ширина строки в единицах шрифта (с учётом запаса)."""
        k, _ = self.mm_per_unit(metrics)
        return self.line_mm / k * (1.0 - self.margin_pct / 100.0)


def settings_path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "PlotterHyphen" / "settings.json"
    return Path.home() / ".config" / "plotter_hyphen" / "settings.json"


def load_settings(path: Path = None) -> Settings:
    path = path or settings_path()
    s = Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return s
    if not isinstance(data, dict):
        return s
    for f in fields(Settings):
        if f.name in data:
            v = data[f.name]
            default = getattr(s, f.name)
            try:
                setattr(s, f.name, type(default)(v))
            except (TypeError, ValueError):
                pass
    return s


def save_settings(s: Settings, path: Path = None) -> None:
    path = path or settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(s), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
