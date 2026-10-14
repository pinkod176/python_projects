"""Порядок и направление штрихов «как при письме рукой».

Работает с готовыми штрихами в координатах .gfont (Y вниз).

Направление:
    открытый штрих — вертикальный/наклонный сверху вниз, пологий слева направо
                      (поэтому «л», «м» начинаются снизу слева, «с», «з» — сверху);
    замкнутая петля — против часовой стрелки (как видно на экране), от верхней
                      точки чуть правее середины («о», «0», петли «б», «в», «д»).
Порядок:
    1) основные штрихи слева направо (при равной позиции — верхний раньше);
    2) перекладины: пологие штрихи в средней части буквы, касающиеся других
       штрихов («Н», «А», «t», «f», «Ж»);
    3) у букв — точки и надстрочные знаки последними («i», «j», «ё», «й», «ї», «á»).
       У знаков препинания («:», «;», «!») точки идут в обычном порядке.
"""

from __future__ import annotations

from functools import cmp_to_key
from typing import List, Sequence

import numpy as np


def _closed(q: np.ndarray) -> bool:
    return len(q) > 3 and np.allclose(q[0], q[-1])


def orient_open(q: np.ndarray) -> np.ndarray:
    d = q[-1] - q[0]
    if abs(d[1]) > 0.6 * abs(d[0]):
        return q if d[1] >= 0 else q[::-1]          # сверху вниз
    return q if d[0] >= 0 else q[::-1]              # слева направо


def orient_closed(q: np.ndarray) -> np.ndarray:
    ring = q[:-1]
    x, y = ring[:, 0], ring[:, 1]
    area = 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    if area > 0:                    # при Y вниз положительная площадь = по часовой на экране
        ring = ring[::-1]
        x, y = ring[:, 0], ring[:, 1]
    w = max(float(np.ptp(x)), 1.0)
    h = max(float(np.ptp(y)), 1.0)
    score = -(y - y.min()) / h + 0.35 * (x - x.mean()) / w     # верх, чуть правее середины
    k = int(np.argmax(score))
    ring = np.vstack([ring[k:], ring[:k]])
    return np.vstack([ring, ring[:1]])


def orient(q: np.ndarray) -> np.ndarray:
    return orient_closed(q) if _closed(q) else orient_open(q)


def _seg_dist(p: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Расстояния от точек p (M×2) до ломаной b (N×2)."""
    if len(b) == 1:
        return np.linalg.norm(p - b[0], axis=1)
    a0, a1 = b[:-1], b[1:]
    ab = a1 - a0
    L2 = np.maximum((ab ** 2).sum(axis=1), 1e-12)
    t = np.clip(((p[:, None, :] - a0[None]) * ab[None]).sum(axis=2) / L2[None], 0.0, 1.0)
    proj = a0[None] + t[..., None] * ab[None]
    return np.linalg.norm(p[:, None, :] - proj, axis=2).min(axis=1)


def _near(a: np.ndarray, b: np.ndarray, tol: float) -> bool:
    """Касаются ли (пересекаются ли) две ломаные — с допуском tol."""
    return bool(min(_seg_dist(a, b).min(), _seg_dist(b, a).min()) <= tol)


def hand_order(strokes: Sequence[np.ndarray], dots: Sequence[bool], *, letter: bool,
               cap: float) -> List[np.ndarray]:
    """Вернуть штрихи в порядке письма, каждый — в направлении письма.

    strokes — штрихи (Nx2, Y вниз); dots[i] — штрих i получен из «точки» (спираль).
    letter  — символ является буквой (тогда точки/надстрочные знаки идут последними).
    cap     — высота заглавных в тех же единицах (масштаб для порогов).
    """
    qs = [np.asarray(q, dtype=float) for q in strokes]
    if not qs:
        return []
    qs = [q if dots[i] else orient(q) for i, q in enumerate(qs)]
    n = len(qs)
    boxes = [(q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()) for q in qs]
    size = [max(b[2] - b[0], b[3] - b[1]) for b in boxes]
    small = [dots[i] or size[i] < 0.3 * cap for i in range(n)]
    big = [i for i in range(n) if not small[i]]

    marks: List[int] = []
    if letter and n > 1:
        # основа буквы — штрихи, доходящие до нижней половины глифа;
        # надстрочный знак — небольшой штрих целиком над основой и не касающийся её
        g_top = min(b[1] for b in boxes)
        g_bot = max(b[3] for b in boxes)
        g_h = max(g_bot - g_top, 1.0)
        body = [i for i in range(n) if boxes[i][3] > g_top + 0.45 * g_h]
        if body:
            body_top = min(boxes[i][1] for i in body)
            for i in range(n):
                if i in body or size[i] > 0.6 * cap:
                    continue
                above = boxes[i][3] <= body_top + 0.1 * g_h
                apart = not any(_near(qs[i], qs[j], 0.04 * cap) for j in body)
                if above and apart:
                    marks.append(i)
                    small[i] = True
            big = [i for i in big if i not in marks]

    bars: List[int] = []
    if len(big) >= 2 or (len(big) == 1 and n > 1):
        top = min(boxes[i][1] for i in big)
        bot = max(boxes[i][3] for i in big)
        hgt = max(bot - top, 1.0)
        tol = 0.08 * cap
        for i in big:
            q = qs[i]
            if _closed(q):
                continue
            d = q[-1] - q[0]
            ymid = 0.5 * (boxes[i][1] + boxes[i][3])
            flat = abs(d[1]) < 0.35 * abs(d[0]) and (boxes[i][3] - boxes[i][1]) < 0.25 * hgt
            middle = top + 0.2 * hgt < ymid < bot - 0.1 * hgt
            if flat and middle and any(_near(q, qs[j], tol) for j in big if j != i):
                bars.append(i)

    rest = [i for i in range(n) if i not in marks and i not in bars]

    def before(i: int, j: int) -> int:
        # штрихи, заметно перекрывающиеся по горизонтали, — одна «колонка»: сверху вниз
        # («З», «Е»); иначе слева направо по центру («Н», «Ы», «Ю», стойка «К» раньше «усов»)
        bi, bj = boxes[i], boxes[j]
        pad = 0.03 * cap                            # у строго вертикального штриха ширина 0
        overlap = min(bi[2], bj[2]) - max(bi[0], bj[0]) + 2 * pad
        narrow = min(bi[2] - bi[0], bj[2] - bj[0]) + 2 * pad
        if overlap > 0.5 * narrow:
            # одна колонка: сравниваем точки начала штрихов (после ориентации)
            si, sj = qs[i][0], qs[j][0]
            if abs(si[1] - sj[1]) > 0.25 * cap:
                return -1 if si[1] < sj[1] else 1   # «З»: верхняя дуга раньше нижней
            return -1 if si[0] <= sj[0] else 1      # «К»: стойка раньше «уса»
        ci, cj = bi[0] + bi[2], bj[0] + bj[2]
        return -1 if ci <= cj else 1

    rest.sort(key=cmp_to_key(before))
    bars.sort(key=lambda i: (boxes[i][1], boxes[i][0]))
    marks.sort(key=lambda i: (boxes[i][0], boxes[i][1]))
    return [qs[i] for i in rest + bars + marks]
