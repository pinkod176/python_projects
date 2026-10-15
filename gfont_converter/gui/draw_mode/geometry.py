"""Клетка холста и разметка тетради.

Холст рисования — клетка WIDTH × HEIGHT «единиц холста» (ось Y вниз, как в .gfont).
Разметка (базовая линия, высота строчных, заглавных, выносные) берётся из пропорций
эталона, те же, что у движка (gfont.normalize): строчные 220, заглавные 315,
выносные вверх 365 и вниз 150 при базовой линии −85.

Штрихи пользователя хранятся в единицах холста; перевод в .gfont делается только при
экспорте: X — от центра клетки, Y — от базовой линии, масштаб k = cap_height / cap.
«Размер шаблона» (size) раздвигает разметку на холсте: буквы рисуются крупнее или мельче,
а в .gfont получаются того же размера (k меняется вместе с разметкой).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from gfont.normalize import TargetMetrics

# Пропорции эталона (см. gfont/normalize.py и README: blood8)
REF_CAP = 315.0
REF_XHEIGHT = 220.0
REF_ASCENDER = 365.0
REF_DESCENDER = 150.0

WIDTH = 820.0           # ширина клетки (≈ 1.5–2 ширины самой широкой буквы)
HEIGHT = 900.0
BASELINE = 615.0        # Y базовой линии в клетке
BASE_CAP = 380.0        # высота заглавных в клетке при size = 1


@dataclass
class CellGeometry:
    size: float = 1.0                                   # «размер шаблона», 0.8 … 1.2
    tm: TargetMetrics = field(default_factory=TargetMetrics)

    # ---- клетка ----
    @property
    def width(self) -> float:
        return WIDTH

    @property
    def height(self) -> float:
        return HEIGHT

    @property
    def cx(self) -> float:
        return WIDTH / 2

    # ---- разметка (Y в клетке) ----
    @property
    def cap(self) -> float:
        """Высота заглавных в единицах клетки."""
        return BASE_CAP * self.size

    @property
    def xheight(self) -> float:
        ratio = (self.tm.x_height / self.tm.cap_height) if self.tm.x_height else REF_XHEIGHT / REF_CAP
        return self.cap * ratio

    @property
    def baseline(self) -> float:
        return BASELINE

    @property
    def xline(self) -> float:
        return BASELINE - self.xheight

    @property
    def capline(self) -> float:
        return BASELINE - self.cap

    @property
    def ascline(self) -> float:
        return BASELINE - self.cap * REF_ASCENDER / REF_CAP

    @property
    def descline(self) -> float:
        return BASELINE + self.cap * REF_DESCENDER / REF_CAP

    def guides(self):
        """(имя, Y) линий тетради сверху вниз."""
        return [("asc", self.ascline), ("cap", self.capline), ("x", self.xline),
                ("base", self.baseline), ("desc", self.descline)]

    # ---- перевод координат ----
    @property
    def k(self) -> float:
        """Единиц .gfont на единицу клетки."""
        return self.tm.cap_height * self.tm.scale / self.cap

    def to_g(self, pts) -> np.ndarray:
        """Клетка -> .gfont (без центрирования по bbox)."""
        p = np.asarray(pts, dtype=float).reshape(-1, 2)
        k = self.k
        return np.stack([(p[:, 0] - self.cx) * k, self.tm.baseline + (p[:, 1] - BASELINE) * k], axis=1)

    def from_g(self, pts) -> np.ndarray:
        """.gfont -> клетка (X = 0 попадает в центр клетки)."""
        p = np.asarray(pts, dtype=float).reshape(-1, 2)
        k = self.k
        return np.stack([self.cx + p[:, 0] / k, BASELINE + (p[:, 1] - self.tm.baseline) / k], axis=1)
