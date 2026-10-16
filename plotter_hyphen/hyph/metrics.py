"""Ширина текста по глифам .gfont.

Модель та же, что у предпросмотра gfont_converter: программа плоттера ставит буквы
по крайним точкам, поэтому ширина буквы — ширина bbox её штрихов, между буквами
добавляется межбуквенный интервал, пробел — отдельная ширина. Всё в единицах
шрифта; перевод в миллиметры — через калибровку (мм на единицу).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set

from .gfont import Strokes

DEFAULT_GAP = 35.0     # межбуквенный интервал, ед. шрифта (как в предпросмотре конвертера)
DEFAULT_SPACE = 110.0  # ширина пробела, ед. шрифта


def bbox(strokes: Strokes):
    xs = [p[0] for s in strokes for p in s]
    ys = [p[1] for s in strokes for p in s]
    return min(xs), max(xs), min(ys), max(ys)


@dataclass
class Metrics:
    widths: Dict[str, float]          # ширина bbox глифа по символу
    gap: float = DEFAULT_GAP
    space: float = DEFAULT_SPACE
    fallback: float = 150.0           # ширина символа, которого нет в шрифте
    missing: Set[str] = field(default_factory=set)

    @classmethod
    def from_glyphs(cls, glyphs: Dict[int, Strokes], gap: float = DEFAULT_GAP,
                    space: float = DEFAULT_SPACE) -> "Metrics":
        widths: Dict[str, float] = {}
        for code, strokes in glyphs.items():
            x0, x1, _, _ = bbox(strokes)
            widths[chr(code)] = max(x1 - x0, 1.0)
        letters = [w for ch, w in widths.items() if "а" <= ch <= "я"]
        pool = letters or list(widths.values())
        fallback = statistics.median(pool) if pool else 150.0
        return cls(widths=widths, gap=gap, space=space, fallback=fallback)

    def has(self, ch: str) -> bool:
        return ch in self.widths

    def char_width(self, ch: str) -> float:
        w = self.widths.get(ch)
        if w is None:
            self.missing.add(ch)
            return self.fallback
        return w

    def text_width(self, text: str) -> float:
        """Ширина строки от левого края первой буквы до правого края последней."""
        total = 0.0
        prev_glyph = False
        for ch in text:
            if ch.isspace():
                total += self.space
                prev_glyph = False
                continue
            if prev_glyph:
                total += self.gap
            total += self.char_width(ch)
            prev_glyph = True
        return total

    def missing_in(self, texts: Iterable[str]) -> List[str]:
        seen = sorted({ch for t in texts for ch in t if not ch.isspace() and ch not in self.widths})
        return seen
