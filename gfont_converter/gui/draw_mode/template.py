"""Шаблон-подсказка под рисуемым символом.

Источник — шрифт-образец (по умолчанию встроенный DejaVu Sans) или свой шаблон .gfont.
Контур символа берётся из шрифта как есть (кривые Безье через fontTools QtPen -> QPainterPath)
и рисуется только обводкой пунктиром.

Размер: строчные буквы масштабируются по x-height шрифта (верх «о» = линия строчных),
всё остальное — по высоте заглавных (sCapHeight): так выносные «б», «р», «у», знаки
препинания, скобки и «@» встают на свои места по метрикам шрифта, а не вписываются в рамку.
По горизонтали — по центру клетки, базовая линия шрифта = базовая линия клетки.

Подсказка «порядок штрихов»: осевая линия образца (скелет из движка конвертера,
gfont.extract) с порядком и направлением по правилам gfont.stroke_order.

Всё кэшируется по (код, размер разметки).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainterPath, QTransform

from gfont.session import resource_dir

from .geometry import CellGeometry

SAMPLE_FONT_NAME = "DejaVuSans.ttf"


def default_sample_font() -> Path:
    return resource_dir() / "sample" / SAMPLE_FONT_NAME


@dataclass
class TemplateShape:
    kind: str                         # outline | strokes | box
    path: QPainterPath = field(default_factory=QPainterPath)
    rect: QRectF = field(default_factory=QRectF)      # для box — рамка; иначе bbox пути
    label: str = ""


@dataclass
class Hint:
    lines: List[np.ndarray]           # осевые линии в единицах клетки, в порядке письма
    dots: List[bool]                  # i-я линия — точка


def _is_lower(code: int) -> bool:
    return unicodedata.category(chr(code)) == "Ll"


def _no_template(code: int) -> bool:
    ch = chr(code)
    return ch.isspace() or unicodedata.category(ch)[0] in ("Z", "C", "M")


class TemplateProvider:
    """Контуры шаблона по коду символа (кэш QPainterPath)."""

    def __init__(self):
        self.font_path: Optional[Path] = None
        self.gfont_path: Optional[Path] = None
        self._src = None
        self._fm = None
        self._gf = None
        self._cache: Dict[Tuple, Optional[TemplateShape]] = {}
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
                return self.set_font(None)
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
        self._cache.clear()
        self._hints.clear()

    # ---- контур ----
    def _transform(self, code: int, geo: CellGeometry) -> Optional[Tuple[float, float]]:
        """(масштаб, X центра bbox в ед. шрифта) для кода."""
        src, fm = self._src, self._fm
        if src is None or not src.has(code):
            return None
        bb = src.bbox(code)
        if bb is None:
            return None
        s = geo.xheight / fm.xheight if _is_lower(code) else geo.cap / fm.cap
        return s, 0.5 * (bb[0] + bb[2])

    def shape(self, code: int, geo: CellGeometry) -> Optional[TemplateShape]:
        key = (code, round(geo.size, 4), bool(self._gf))
        if key not in self._cache:
            try:
                self._cache[key] = self._make(code, geo)
            except Exception:  # noqa: BLE001 — шаблон не должен ронять окно
                self._cache[key] = self._box(code, geo)
        return self._cache[key]

    def _make(self, code: int, geo: CellGeometry) -> Optional[TemplateShape]:
        if _no_template(code):
            return None
        if self._gf is not None:
            if code in self._gf:
                strokes = [s for s in self._gf.strokes(code) if len(s) >= 1]
                if strokes:
                    path = QPainterPath()
                    for s in strokes:
                        p = geo.from_g(s)
                        path.moveTo(*p[0])
                        if len(p) == 1:
                            path.lineTo(p[0][0] + 0.5, p[0][1])
                        for x, y in p[1:]:
                            path.lineTo(x, y)
                    return TemplateShape("strokes", path, path.boundingRect())
            return self._box(code, geo)
        tf = self._transform(code, geo)
        if tf is None:
            return self._box(code, geo)
        from fontTools.pens.qtPen import QtPen
        s, bcx = tf
        pen = QtPen(self._src.glyphset, path=QPainterPath())
        self._src.glyphset[self._src.cmap[code]].draw(pen)
        t = QTransform(s, 0, 0, -s, geo.cx - bcx * s, geo.baseline)
        path = t.map(pen.path)
        if path.isEmpty():
            return self._box(code, geo)
        return TemplateShape("outline", path, path.boundingRect())

    def _box(self, code: int, geo: CellGeometry) -> TemplateShape:
        """Символа нет в образце: пунктирная рамка нужной высоты и сам символ серым."""
        h = geo.xheight if _is_lower(code) else geo.cap
        w = 0.7 * h
        r = QRectF(geo.cx - w / 2, geo.baseline - h, w, h)
        return TemplateShape("box", QPainterPath(), r, chr(code))

    # ---- осевая линия и порядок ----
    def hint(self, code: int, geo: CellGeometry) -> Optional[Hint]:
        key = (code, round(geo.size, 4), bool(self._gf))
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
            if code not in self._gf:
                return None
            lines = [geo.from_g(s) for s in self._gf.strokes(code) if len(s) >= 2]
            return Hint(lines, [False] * len(lines))
        tf = self._transform(code, geo)
        if tf is None:
            return None
        s, bcx = tf
        shape = extract_glyph(self._src, code, "skeleton", self._fm.cap, ExtractParams())

        def to_cell(p):
            p = np.asarray(p, dtype=float).reshape(-1, 2)
            return np.stack([geo.cx + (p[:, 0] - bcx) * s, geo.baseline - p[:, 1] * s], axis=1)

        lines = []
        for pts, _closed in shape.strokes:
            q = to_cell(pts)
            idx = rdp(q, 2.0)
            lines.append(q[idx] if len(idx) >= 2 else q)
        n = len(lines)
        for cx, cy, _r in shape.dots:
            lines.append(to_cell([[cx, cy]]))
        dots = [i >= n for i in range(len(lines))]
        if not lines:
            return None
        letter = unicodedata.category(chr(code)).startswith("L")
        ordered = hand_order(lines, dots, letter=letter, cap=geo.cap)
        return Hint(ordered, [len(q) == 1 for q in ordered])
