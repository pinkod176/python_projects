"""Правка символа проекта без Qt: штрихи, отмена/повтор, правка точек.

Общая часть для холста настольной версии (canvas.py) и Android (android_api.py).
Стек отмены — свой для каждой пары (символ, вариант), хранит копии GlyphEntry.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .geometry import CellGeometry
from .project import DRAWN, EMPTY, GlyphEntry, Project, Stroke
from .strokes import process_stroke

UNDO_LIMIT = 200


def processed_cell(strokes: Sequence[Stroke], project: Project) -> List[np.ndarray]:
    """Обработанные штрихи (как будут в файле) в единицах клетки холста."""
    geo: CellGeometry = project.geometry()
    st = project.settings
    out = []
    for s in strokes:
        q = process_stroke(s, geo, st.smoothing, st.density)
        out.append(geo.from_g(q) if len(q) else q)
    return out


class GlyphEditor:
    def __init__(self, project: Optional[Project] = None):
        self.project = project
        self.code = ord("а")
        self.variant = 0
        self._undo: Dict[Tuple[int, int], List[GlyphEntry]] = {}
        self._redo: Dict[Tuple[int, int], List[GlyphEntry]] = {}

    def set_project(self, project: Project) -> None:
        self.project = project
        self._undo.clear()
        self._redo.clear()

    def select(self, code: int, variant: int = 0) -> None:
        self.code = code
        self.variant = variant

    # ---- доступ ----
    def _key(self) -> Tuple[int, int]:
        return (self.code, self.variant)

    def entry(self) -> GlyphEntry:
        return self.project.entry(self.code)

    def strokes(self) -> List[Stroke]:
        e = self.project.glyphs.get(self.code) if self.project else None
        if e is None or self.variant >= len(e.variants):
            return []
        return e.variants[self.variant]

    def _ensure_variant(self) -> List[Stroke]:
        e = self.entry()
        while len(e.variants) <= self.variant:
            e.variants.append([])
        return e.variants[self.variant]

    # ---- отмена ----
    def push_undo(self) -> None:
        st = self._undo.setdefault(self._key(), [])
        st.append(self.entry().copy())
        if len(st) > UNDO_LIMIT:
            st.pop(0)
        self._redo.pop(self._key(), None)

    def touch(self) -> None:
        """Обновить статус символа после правки и пометить проект изменённым."""
        e = self.entry()
        if any(e.variants):
            e.status = DRAWN
        elif e.status == DRAWN:
            e.status = EMPTY
        self.project.dirty = True

    def can_undo(self) -> bool:
        return bool(self._undo.get(self._key()))

    def can_redo(self) -> bool:
        return bool(self._redo.get(self._key()))

    def undo(self) -> bool:
        st = self._undo.get(self._key())
        if not st:
            return False
        self._redo.setdefault(self._key(), []).append(self.entry().copy())
        self.project.glyphs[self.code] = st.pop()
        self.touch()
        return True

    def redo(self) -> bool:
        st = self._redo.get(self._key())
        if not st:
            return False
        self._undo.setdefault(self._key(), []).append(self.entry().copy())
        self.project.glyphs[self.code] = st.pop()
        self.touch()
        return True

    # ---- штрихи ----
    def add_stroke(self, s: Stroke) -> None:
        self.push_undo()
        self._ensure_variant().append(s)
        e = self.entry()
        if e.source in ("font", "similar", ""):
            e.source = "user"
        self.touch()

    def delete_last(self) -> bool:
        if not self.strokes():
            return False
        self.push_undo()
        self._ensure_variant().pop()
        self.touch()
        return True

    def clear(self) -> bool:
        if not self.strokes():
            return False
        self.push_undo()
        self._ensure_variant().clear()
        self.touch()
        return True

    def delete_stroke(self, i: int) -> bool:
        if not 0 <= i < len(self.strokes()):
            return False
        self.push_undo()
        del self._ensure_variant()[i]
        self.touch()
        return True

    def replace(self, entry: GlyphEntry) -> None:
        """Заменить символ целиком (заполнение, импорт) с возможностью отмены."""
        self.push_undo()
        self.project.glyphs[self.code] = entry
        self.touch()

    # ---- правка точек ----
    def begin_point_edit(self, i: int) -> List[Tuple[float, float]]:
        """Штрих i становится «готовым» (fixed): его точки — обработанные точки,
        которые видит пользователь; их можно двигать. Возвращает эти точки."""
        self.push_undo()
        strokes = self._ensure_variant()
        q = processed_cell([strokes[i]], self.project)[0]
        strokes[i] = Stroke([(float(x), float(y)) for x, y in q], dot=False, fixed=True)
        self.entry().source = "user"
        self.touch()
        return strokes[i].pts

    def move_point(self, i: int, j: int, x: float, y: float) -> None:
        s = self._ensure_variant()[i]
        pts = list(s.pts)
        closed = len(pts) > 3 and pts[0] == pts[-1]
        pts[j] = (float(x), float(y))
        if closed and j in (0, len(pts) - 1):
            pts[0] = pts[-1] = pts[j]
        s.pts = pts
        self.project.dirty = True
