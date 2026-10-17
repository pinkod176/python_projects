"""Фасад движка для интерфейсов (GUI). Не зависит от Qt.

Хранит открытый шрифт и кэш извлечённых форм: дорогое извлечение (растр, скелет)
выполняется один раз на символ и режим, а наклон/масштаб/интервал/сглаживание/живость
пересчитываются быстро. Сохранение идёт через тот же build.convert, что и в CLI.
"""

from __future__ import annotations

import os
import sys
import threading
import unicodedata
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .build import (ConvertOptions, ConvertReport, convert, effective_extract_params,
                    resolve_mode, shape_key)
from .calibrate import build_calibration
from .charset import FALLBACKS, parse_charset
from .extract import ExtractParams, FontSource, extract_glyph
from .format import decode_glyph, encode_glyph
from .normalize import TargetMetrics, font_scale, measure_font, place_glyph, place_outline

CHARSET_PRESETS: Dict[str, Tuple[str, Optional[str]]] = {
    "ru_en": ("Русский + английский + цифры + знаки", "ascii,russian,punct,chars:«»°§©®±×÷·"),
    "ru": ("Только русские", "russian"),
    "en": ("Только английские", "U+0041-U+005A,U+0061-U+007A"),
    "full": ("Полный: кириллица, латиница-1, знаки", "default"),
    "custom": ("Свой набор", None),
}

DEFAULT_PREVIEW_TEXT = ("Съешь же ещё этих мягких французских булок, да выпей чаю. "
                        "The quick brown fox jumps over the lazy dog. "
                        "0123456789 № % @ * ( ) « » — – ‑ ! ? : ; ,")

DEFAULT_TEMPLATE_NAME = "с_клода_дополненный.gfont"


def resource_dir() -> Path:
    """Папка resources/ рядом с кодом, внутри собранного exe (PyInstaller) или
    указанная в GFONT_RESOURCES (Android: файлы распакованы в память приложения)."""
    env = os.environ.get("GFONT_RESOURCES")
    if env:
        return Path(env)
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "resources"


def default_template_path() -> Path:
    return resource_dir() / DEFAULT_TEMPLATE_NAME


@dataclass
class UiParams:
    """Параметры, которые меняет пользователь в окне."""
    mode: str = "skeleton"           # skeleton | outline | auto
    charset_preset: str = "ru_en"
    custom_chars: str = ""
    slant: float = 0.0               # градусы
    scale: float = 1.0
    spacing: float = 1.0             # ширина букв по X (см. README: интервал неизвестен)
    density: float = 1.0             # плотность точек: шаг = 25 / density
    smooth: float = 3.0
    hand_order: bool = True          # порядок штрихов как при письме рукой
    overhang: float = 0.35           # хвосты строчных за пределами основы (1.0 = как в шрифте)
    liveliness: float = 0.0          # 0..1 («живость почерка» 0–100 %)
    seed: int = 1
    no_new_entries: bool = False
    replace_old: bool = False        # удалять буквы шаблона, которых нет в шрифте (строго один стиль)

    @classmethod
    def from_dict(cls, d: dict) -> "UiParams":
        names = {f.name for f in fields(cls)}
        p = cls()
        for k, v in (d or {}).items():
            if k in names:
                try:
                    setattr(p, k, type(getattr(p, k))(v))
                except (TypeError, ValueError):
                    pass
        return p

    def to_dict(self) -> dict:
        return asdict(self)

    def charset_spec(self) -> str:
        if self.charset_preset == "custom" or self.charset_preset not in CHARSET_PRESETS:
            text = self.custom_chars.strip()
            return "chars:" + text if text else "ascii"
        return CHARSET_PRESETS[self.charset_preset][1]

    def metrics(self) -> TargetMetrics:
        return TargetMetrics(scale=self.scale, slant_deg=self.slant, spacing=self.spacing,
                             step=25.0 / max(self.density, 0.1), smooth=self.smooth,
                             overhang=self.overhang, hand_order=self.hand_order)

    @property
    def variation(self) -> float:
        return 1.5 * max(0.0, self.liveliness)


@dataclass
class GlyphResult:
    code: int
    strokes: List[List[Tuple[float, float]]]
    warnings: List[str]
    src_code: Optional[int]
    cx: float = 0.0


def diagnose(strokes, tm: TargetMetrics) -> List[str]:
    """Признаки сомнительного глифа (для значка предупреждения)."""
    w: List[str] = []
    if not strokes or not any(len(s) >= 2 for s in strokes):
        return ["пустой глиф"]
    pts = np.array([p for s in strokes for p in s])
    if len(strokes) > 8:
        w.append(f"много штрихов ({len(strokes)})")
    if len(pts) > 300:
        w.append(f"очень много точек ({len(pts)})")
    top = tm.baseline - 1.5 * tm.cap_height
    bottom = tm.baseline + 0.8 * tm.cap_height
    if pts[:, 1].min() < top or pts[:, 1].max() > bottom:
        w.append("выходит за метрики по вертикали")
    if pts[:, 0].max() - pts[:, 0].min() > 2.0 * tm.cap_height:
        w.append("слишком широкий")
    return w


class FontSession:
    """Открытый шрифт + кэш форм. Методы glyph()/outline() вызывать из ОДНОГО потока."""

    def __init__(self, path):
        self.path = Path(path)
        self.src = FontSource(self.path)
        self.fm = measure_font(self.src)
        self.cache: dict = {}
        self.lock = threading.Lock()
        self._mode_cache: Dict[str, str] = {}

    # ---- сведения ----
    @property
    def family(self) -> str:
        return self.src.family_name

    @property
    def glyph_count(self) -> int:
        return len(self.src.cmap)

    def coverage(self, codes: Sequence[int]) -> Tuple[List[int], List[int]]:
        have, miss = [], []
        for c in codes:
            (have if self.source_code(c) is not None else miss).append(c)
        return have, miss

    def source_code(self, code: int) -> Optional[int]:
        if self.src.has(code):
            return code
        for fb in FALLBACKS.get(code, []):
            if self.src.has(fb):
                return fb
        return None

    def mode(self, requested: str) -> str:
        if requested not in self._mode_cache:
            self._mode_cache[requested] = resolve_mode(self.src, requested)
        return self._mode_cache[requested]

    def scale(self, tm: TargetMetrics) -> float:
        return font_scale(self.fm, tm)

    # ---- глифы ----
    def glyph(self, code: int, p: UiParams) -> GlyphResult:
        tm = p.metrics()
        sc = self.source_code(code)
        if sc is None:
            return GlyphResult(code, [], ["нет в шрифте"], None)
        s = self.scale(tm)
        mode = self.mode(p.mode)
        params = effective_extract_params(ExtractParams(), tm, s)
        key = shape_key(sc, mode, params)
        with self.lock:
            shape = self.cache.get(key)
        if shape is None:
            shape = extract_glyph(self.src, sc, mode, self.fm.cap, params)
            with self.lock:
                self.cache[key] = shape
        rng = np.random.default_rng([p.seed, code]) if p.variation > 0 else None
        info: dict = {}
        strokes = (place_glyph(shape, s, tm, p.variation, rng, info,
                               lowercase=unicodedata.category(chr(code)) == "Ll",
                               xheight=self.fm.xheight,
                               uppercase=unicodedata.category(chr(code)) == "Lu",
                               cap=self.fm.cap,
                               letter=unicodedata.category(chr(code)).startswith("L"))
                   if not shape.empty else [])
        if strokes:
            # ровно то, что будет записано в файл (float32)
            strokes = decode_glyph(encode_glyph(code, strokes))[1]
        return GlyphResult(code, strokes, diagnose(strokes, tm), sc, info.get("cx", 0.0))

    def outline(self, code: int, p: UiParams, cx: float):
        sc = self.source_code(code)
        if sc is None:
            return []
        tm = p.metrics()
        return place_outline(self.src.contours(sc), self.scale(tm), tm, cx)

    # ---- сохранение ----
    def options(self, p: UiParams, output, template) -> ConvertOptions:
        return ConvertOptions(
            font=str(self.path), output=str(output), template=str(template), mode=p.mode,
            charset=p.charset_spec(), no_new_entries=p.no_new_entries,
            preserve_template_extra=not p.replace_old, drop_template_noncjk=p.replace_old, variation=p.variation, seed=p.seed,
            metrics=p.metrics())

    def convert(self, p: UiParams, output, template, *, progress=None, cancel=None,
                log=print, jobs: int = 0) -> ConvertReport:
        opts = self.options(p, output, template)
        opts.jobs = jobs
        with self.lock:
            snapshot = dict(self.cache)
        opts.shape_cache = snapshot
        opts.progress = progress
        opts.cancel = cancel
        rep = convert(opts, log=log)
        with self.lock:
            self.cache.update(snapshot)
        return rep


def make_calibration(template, output, p: Optional[UiParams] = None):
    tm = (p or UiParams()).metrics()
    return build_calibration(str(template), str(output), tm)


def variant_paths(folder, family: str, n: int) -> List[Path]:
    """<ИмяШрифта>_1.gfont … <ИмяШрифта>_N.gfont."""
    safe = "".join(ch if ch not in '<>:"/\\|?*' else "_" for ch in family).strip() or "font"
    return [Path(folder) / f"{safe}_{i}.gfont" for i in range(1, n + 1)]
