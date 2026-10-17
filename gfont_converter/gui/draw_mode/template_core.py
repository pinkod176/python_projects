"""Шаблон-подсказка без Qt: источник (шрифт-образец или .gfont), масштаб и положение
символа по метрикам шрифта, контуры ломаными, рамка, осевая линия с порядком штрихов.

Используется окном настольной версии (template.py рисует контур кривыми через Qt)
и Android (android_api.py получает ломаные). Правила размещения — в template.py.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from gfont.session import resource_dir

from .geometry import CellGeometry

SAMPLE_FONT_NAME = "DejaVuSans.ttf"


def default_sample_font() -> Path:
    return resource_dir() / "sample" / SAMPLE_FONT_NAME


@dataclass
class Hint:
    lines: List[np.ndarray]           # осевые линии в единицах клетки, в порядке письма
    dots: List[bool]                  # i-я линия — точка


def is_lower(code: int) -> bool:
    return unicodedata.category(chr(code)) == "Ll"


def no_template(code: int) -> bool:
    ch = chr(code)
    return ch.isspace() or unicodedata.category(ch)[0] in ("Z", "C", "M")


def box_rect(code: int, geo: CellGeometry) -> Tuple[float, float, float, float]:
    """Рамка (x, y, w, h) для символа, которого нет в образце: высота строчной или заглавной."""
    h = geo.xheight if is_lower(code) else geo.cap
    w = 0.7 * h
    return geo.cx - w / 2, geo.baseline - h, w, h


class SampleSource:
    """Откуда берётся шаблон: шрифт-образец TTF/OTF (по умолчанию встроенный) или .gfont."""

    def __init__(self):
        self.font_path: Optional[Path] = None
        self.gfont_path: Optional[Path] = None
        self._src = None
        self._fm = None
        self._gf = None
        self._hints: Dict[Tuple, Optional[Hint]] = {}
        self.error = ""
        self.set_font(None)

    # ---- источник ----
    @property
    def source_name(self) -> str:
        if self.gfont_path:
            return self.gfont_path.name
        if self._src is not None:
            return self._src.family_name
        return "нет"

    def set_font(self, path: Optional[str]) -> None:
        """Шрифт-образец TTF/OTF; None или "" — встроенный."""
        from gfont.extract import FontSource
        from gfont.normalize import measure_font
        p = Path(path) if path else default_sample_font()
        self.error = ""
        try:
            src = FontSource(p)
            fm = measure_font(src)
        except Exception as exc:  # noqa: BLE001 — покажем текст в окне
            self.error = str(exc)
            if path:              # свой шрифт не открылся — берём встроенный
                err = self.error
                self.set_font(None)
                self.error = err
                return
            src = fm = None
        self._src, self._fm = src, fm
        self.font_path = p
        self.gfont_path = None
        self._gf = None
        self.clear_cache()

    def set_gfont(self, path: str) -> None:
        """Свой шаблон-подсказка .gfont: его штрихи показываются пунктиром."""
        from gfont.format import read_gfont
        self._gf = read_gfont(path)
        self.gfont_path = Path(path)
        self.clear_cache()

    def clear_cache(self) -> None:
        self._hints.clear()

    def _key(self, code: int, geo: CellGeometry) -> Tuple:
        return (code, round(geo.size, 4), bool(self._gf))

    # ---- размещение ----
    def transform(self, code: int, geo: CellGeometry) -> Optional[Tuple[float, float]]:
        """(масштаб, X центра bbox в ед. шрифта): строчные — по x-height, остальное — по
        высоте заглавных; базовая линия шрифта = базовая линия клетки."""
        src, fm = self._src, self._fm
        if self._gf is not None or src is None or not src.has(code):
            return None
        bb = src.bbox(code)
        if bb is None:
            return None
        s = geo.xheight / fm.xheight if is_lower(code) else geo.cap / fm.cap
        return s, 0.5 * (bb[0] + bb[2])

    def to_cell(self, pts, code: int, geo: CellGeometry, tf) -> np.ndarray:
        s, bcx = tf
        p = np.asarray(pts, dtype=float).reshape(-1, 2)
        return np.stack([geo.cx + (p[:, 0] - bcx) * s, geo.baseline - p[:, 1] * s], axis=1)

    def gfont_strokes(self, code: int, geo: CellGeometry) -> Optional[List[np.ndarray]]:
        """Штрихи своего шаблона .gfont в единицах клетки (None — нет такого символа)."""
        if self._gf is None or code not in self._gf:
            return None
        out = [geo.from_g(s) for s in self._gf.strokes(code) if len(s) >= 1]
        return out or None

    def outline_polys(self, code: int, geo: CellGeometry) -> Optional[List[np.ndarray]]:
        """Контуры символа образца ломаными в единицах клетки (None — нет в образце)."""
        tf = self.transform(code, geo)
        if tf is None:
            return None
        polys = [self.to_cell(c, code, geo, tf) for c in self._src.contours(code)]
        return [q for q in polys if len(q) >= 2] or None

    def describe(self, code: int, geo: CellGeometry) -> Optional[dict]:
        """Шаблон для отрисовки без Qt: {"kind", "polys", "closed", "rect", "label"}."""
        if no_template(code):
            return None
        try:
            if self._gf is not None:
                polys, kind, closed = self.gfont_strokes(code, geo), "strokes", False
            else:
                polys, kind, closed = self.outline_polys(code, geo), "outline", True
        except Exception:  # noqa: BLE001 — шаблон не должен ронять приложение
            polys = None
        if not polys:
            return {"kind": "box", "polys": [], "closed": False,
                    "rect": list(box_rect(code, geo)), "label": chr(code)}
        allp = np.vstack(polys)
        x0, y0 = allp.min(axis=0)
        x1, y1 = allp.max(axis=0)
        return {"kind": kind, "polys": polys, "closed": closed,
                "rect": [float(x0), float(y0), float(x1 - x0), float(y1 - y0)], "label": ""}

    # ---- осевая линия и порядок ----
    def hint(self, code: int, geo: CellGeometry) -> Optional[Hint]:
        key = self._key(code, geo)
        if key not in self._hints:
            try:
                self._hints[key] = self._make_hint(code, geo)
            except Exception:  # noqa: BLE001
                self._hints[key] = None
        return self._hints[key]

    def _make_hint(self, code: int, geo: CellGeometry) -> Optional[Hint]:
        from gfont.extract import ExtractParams, extract_glyph
        from gfont.normalize import rdp
        from gfont.stroke_order import hand_order

        if self._gf is not None:
            lines = [q for q in (self.gfont_strokes(code, geo) or []) if len(q) >= 2]
            return Hint(lines, [False] * len(lines)) if lines else None
        tf = self.transform(code, geo)
        if tf is None:
            return None
        shape = extract_glyph(self._src, code, "skeleton", self._fm.cap, ExtractParams())
        lines = []
        for pts, _closed in shape.strokes:
            q = self.to_cell(pts, code, geo, tf)
            idx = rdp(q, 2.0)
            lines.append(q[idx] if len(idx) >= 2 else q)
        n = len(lines)
        for cx, cy, _r in shape.dots:
            lines.append(self.to_cell([[cx, cy]], code, geo, tf))
        dots = [i >= n for i in range(len(lines))]
        if not lines:
            return None
        letter = unicodedata.category(chr(code)).startswith("L")
        ordered = hand_order(lines, dots, letter=letter, cap=geo.cap)
        return Hint(ordered, [len(q) == 1 for q in ordered])
