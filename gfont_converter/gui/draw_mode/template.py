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

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainterPath, QTransform

from .geometry import CellGeometry
from .template_core import Hint, SampleSource, box_rect, default_sample_font, no_template

__all__ = ["Hint", "TemplateProvider", "TemplateShape", "default_sample_font"]


@dataclass
class TemplateShape:
    kind: str                         # outline | strokes | box
    path: QPainterPath = field(default_factory=QPainterPath)
    rect: QRectF = field(default_factory=QRectF)      # для box — рамка; иначе bbox пути
    label: str = ""


class TemplateProvider(SampleSource):
    """Шаблон для холста Qt: контур кривыми Безье (fontTools QtPen), кэш QPainterPath."""

    def __init__(self):
        self._cache: Dict[Tuple, Optional[TemplateShape]] = {}
        super().__init__()

    def clear_cache(self) -> None:
        super().clear_cache()
        self._cache.clear()

    def shape(self, code: int, geo: CellGeometry) -> Optional[TemplateShape]:
        key = self._key(code, geo)
        if key not in self._cache:
            try:
                self._cache[key] = self._make(code, geo)
            except Exception:  # noqa: BLE001 — шаблон не должен ронять окно
                self._cache[key] = self._box(code, geo)
        return self._cache[key]

    def _make(self, code: int, geo: CellGeometry) -> Optional[TemplateShape]:
        if no_template(code):
            return None
        if self._gf is not None:
            strokes = self.gfont_strokes(code, geo)
            if not strokes:
                return self._box(code, geo)
            path = QPainterPath()
            for p in strokes:
                path.moveTo(*p[0])
                if len(p) == 1:
                    path.lineTo(p[0][0] + 0.5, p[0][1])
                for x, y in p[1:]:
                    path.lineTo(x, y)
            return TemplateShape("strokes", path, path.boundingRect())
        tf = self.transform(code, geo)
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
        return TemplateShape("box", QPainterPath(), QRectF(*box_rect(code, geo)), chr(code))
