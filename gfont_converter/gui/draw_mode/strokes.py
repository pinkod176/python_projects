"""Обработка нарисованного штриха и перевод глифа в координаты .gfont (без Qt).

Штрих при отпускании кнопки:
    1) точки мыши -> единицы .gfont (geometry.to_g), убрать повторы и дрожание (порог по расстоянию);
    2) сгладить: сначала лёгкое сглаживание дрожания руки, затем гаусс между углами — тот же
       код, что в конвертере (normalize.refine_stroke): острые углы сохраняются; при 0 %
       сглаживания точки только прореживаются;
    3) передискретизировать с равномерным шагом (25 / плотность), первая и последняя точка остаются;
    4) клик без движения = точка -> маленькая спираль из 6 точек (normalize.spiral), как в конвертере.
Хранится сырой штрих в единицах холста, поэтому сглаживание и плотность можно менять потом.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from gfont.normalize import (TargetMetrics, _smooth_closed, _smooth_open, polyline_length,
                             refine_stroke, resample, spiral)

from .charsets import CAP_LETTERS, XHEIGHT_LETTERS, can_align
from .geometry import CellGeometry
from .project import Stroke

SMOOTH_MAX = 12.0      # сигма гауссова сглаживания при 100 %, ед. .gfont
PRE_SMOOTH = 4.0       # предварительное сглаживание дрожания руки при 100 %, ед. .gfont
JITTER_DIST = 1.5      # точки ближе этого (ед. .gfont) считаются дрожанием
DOT_LEN = 5.0          # штрих короче этого (ед. .gfont) — точка
ALIGN_TOL = 0.12       # автовыравнивание: подтягиваем, если низ не дальше 0.12 высоты заглавных

Point = Tuple[float, float]


def step_for(density: float) -> float:
    return 25.0 / max(0.1, density)


def metrics_for(geo: CellGeometry, smoothing: float, density: float) -> TargetMetrics:
    return replace(geo.tm, step=step_for(density), smooth=SMOOTH_MAX * max(0.0, smoothing))


def clean_points(p: np.ndarray, min_dist: float) -> np.ndarray:
    """Убрать повторы и мелкое дрожание: соседние точки ближе min_dist отбрасываются
    (последняя точка всегда остаётся)."""
    if len(p) < 2:
        return p
    keep = [0]
    for i in range(1, len(p)):
        if np.hypot(*(p[i] - p[keep[-1]])) >= min_dist:
            keep.append(i)
    if keep[-1] != len(p) - 1:
        if len(keep) > 1 and np.hypot(*(p[-1] - p[keep[-1]])) < min_dist:
            keep[-1] = len(p) - 1
        else:
            keep.append(len(p) - 1)
    return p[keep]


def is_dot_like(g: np.ndarray) -> bool:
    return len(g) < 2 or polyline_length(g) < DOT_LEN


def process_stroke(s: Stroke, geo: CellGeometry, smoothing: float, density: float) -> np.ndarray:
    """Штрих (единицы холста) -> обработанная ломаная в единицах .gfont (X от центра клетки)."""
    tm = metrics_for(geo, smoothing, density)
    g = geo.to_g(s.pts) if s.pts else np.zeros((0, 2))
    if len(g) == 0:
        return g
    if s.fixed and not s.dot:
        return g
    if s.dot or is_dot_like(clean_points(g, JITTER_DIST)):
        c = g.mean(axis=0)
        return spiral(float(c[0]), float(c[1]), 0.0, tm)
    g = clean_points(g, JITTER_DIST)
    L = polyline_length(g)
    closed = (len(g) >= 5 and L > 4 * tm.step
              and np.hypot(*(g[-1] - g[0])) < max(0.6 * tm.step, 12.0))
    if closed:
        g = g.copy()
        g[-1] = g[0]
    ends = g[0].copy(), g[-1].copy()
    if smoothing > 0:
        # дрожание руки убираем до поиска углов, иначе каждый зубчик считается углом
        g = resample(g, 1.5, min_pts=2)
        if closed:
            g[-1] = g[0]
        sig = PRE_SMOOTH * smoothing
        g = _smooth_closed(g, sig) if closed else _smooth_open(g, sig)
    q = refine_stroke(g, closed, tm)
    if len(q) < 2:
        q = np.vstack([g[0], g[-1]])
    if not closed:
        q[0], q[-1] = ends          # начало и конец штриха — там, где их поставил пользователь
    return q


def glyph_raw_g(strokes: Sequence[Stroke], geo: CellGeometry, smoothing: float,
                density: float) -> List[np.ndarray]:
    """Все штрихи глифа в .gfont, без центрирования и выравнивания (в порядке рисования)."""
    out = []
    for s in strokes:
        q = process_stroke(s, geo, smoothing, density)
        if len(q) >= 2:
            out.append(q)
    return out


def align_shift(qs: List[np.ndarray], code: int, tm: TargetMetrics) -> float:
    """Сдвиг по Y, подтягивающий низ основы к базовой линии (0 — не трогать)."""
    if not qs or not can_align(code):
        return 0.0
    bottom = max(float(q[:, 1].max()) for q in qs)       # Y вниз: низ = максимум
    d = tm.baseline - bottom
    return d if abs(d) <= ALIGN_TOL * tm.cap_height * tm.scale else 0.0


def finalize(qs: List[np.ndarray], *, code: int, tm: TargetMetrics, autoalign: bool,
             factor: float = 1.0) -> List[List[Point]]:
    """Выравнивание, нормализация размера (factor, от базовой линии) и X по центру bbox."""
    if not qs:
        return []
    qs = [q.copy() for q in qs]
    if autoalign:
        dy = align_shift(qs, code, tm)
        for q in qs:
            q[:, 1] += dy
    if abs(factor - 1.0) > 1e-6:
        allp = np.vstack(qs)
        cx = 0.5 * (allp[:, 0].min() + allp[:, 0].max())
        for q in qs:
            q[:, 0] = cx + (q[:, 0] - cx) * factor
            q[:, 1] = tm.baseline + (q[:, 1] - tm.baseline) * factor
    allp = np.vstack(qs)
    cx = 0.5 * (allp[:, 0].min() + allp[:, 0].max())
    return [[(float(x - cx), float(y)) for x, y in q] for q in qs]


def glyph_to_gfont(strokes: Sequence[Stroke], geo: CellGeometry, *, code: int, smoothing: float,
                   density: float, autoalign: bool, factor: float = 1.0) -> List[List[Point]]:
    """Штрихи проекта -> штрихи .gfont (как они будут записаны в файл)."""
    qs = glyph_raw_g(strokes, geo, smoothing, density)
    return finalize(qs, code=code, tm=geo.tm, autoalign=autoalign, factor=factor)


# --------------------------------------------------------------------------
# Статистика размеров (предупреждение и «Нормализовать размеры»)
# --------------------------------------------------------------------------

def _height(qs: List[np.ndarray], tm: TargetMetrics) -> float:
    top = min(float(q[:, 1].min()) for q in qs)
    return tm.baseline - top


def size_stats(glyphs: Dict[int, List[np.ndarray]], tm: TargetMetrics) -> Tuple[Optional[float], Optional[float]]:
    """Медианная высота строчных (по буквам с верхом на x-height) и заглавных, ед. .gfont."""
    lo = [_height(q, tm) for c, q in glyphs.items() if q and chr(c) in XHEIGHT_LETTERS]
    up = [_height(q, tm) for c, q in glyphs.items() if q and chr(c) in CAP_LETTERS]
    med = lambda v: float(np.median(v)) if v else None  # noqa: E731
    return med(lo), med(up)


def ratio_warning(glyphs: Dict[int, List[np.ndarray]], tm: TargetMetrics) -> str:
    xh, cap = size_stats(glyphs, tm)
    if xh and cap and xh > 0.92 * cap:
        return (f"Строчные ({xh:.0f}) почти такой же высоты, как заглавные ({cap:.0f}). "
                "Обычно строчные ниже — ориентируйтесь на синюю линию.")
    if xh and cap and xh < 0.45 * cap:
        return (f"Строчные ({xh:.0f}) намного ниже заглавных ({cap:.0f}). "
                "Проверьте, что строчные доходят до синей линии.")
    return ""


def normalize_factors(glyphs: Dict[int, List[np.ndarray]], tm: TargetMetrics) -> Dict[int, float]:
    """Множители, подгоняющие строчные к одной x-height, заглавные к одной высоте
    (по медиане нарисованного). Остальные символы не меняются. Предел 0.8…1.25."""
    xh, cap = size_stats(glyphs, tm)
    out: Dict[int, float] = {}
    for c, qs in glyphs.items():
        if not qs:
            continue
        ch = chr(c)
        target = xh if ch in XHEIGHT_LETTERS else cap if ch in CAP_LETTERS else None
        if not target:
            continue
        h = _height(qs, tm)
        if h > 1.0:
            out[c] = float(min(1.25, max(0.8, target / h)))
    return out


# --------------------------------------------------------------------------
# Варьированные копии (для альтернативных записей)
# --------------------------------------------------------------------------

def vary(strokes: List[List[Point]], rng: np.random.Generator, amount: float = 1.0) -> List[List[Point]]:
    """Слегка изменённая копия глифа .gfont: наклон, масштаб, поворот, плавное дрожание."""
    if not strokes:
        return strokes
    allp = np.array([p for s in strokes for p in s], dtype=float)
    cx = 0.5 * (allp[:, 0].min() + allp[:, 0].max())
    cy = 0.5 * (allp[:, 1].min() + allp[:, 1].max())
    sl = math.tan(math.radians(rng.normal(0, 2.5) * amount))
    sc = 1.0 + rng.normal(0, 0.03) * amount
    rot = math.radians(rng.normal(0, 1.5) * amount)
    c, s_ = math.cos(rot), math.sin(rot)
    out = []
    for st in strokes:
        q = np.asarray(st, dtype=float)
        x, y = (q[:, 0] - cx) * sc, (q[:, 1] - cy) * sc
        x, y = x * c - y * s_, x * s_ + y * c
        x = x - y * sl
        n = len(q)
        noise = rng.normal(0, 1, size=(n, 2))
        if n > 2:
            ker = np.ones(3) / 3.0
            noise = np.stack([np.convolve(noise[:, i], ker, mode="same") for i in range(2)], axis=1)
        noise *= 1.2 * amount
        closed = n > 3 and np.allclose(q[0], q[-1])
        x = x + cx + noise[:, 0]
        y = y + cy + noise[:, 1]
        if closed:
            x[-1], y[-1] = x[0], y[0]
        out.append(list(zip(x.tolist(), y.tolist())))
    allp = np.array([p for s in out for p in s])
    dx = 0.5 * (allp[:, 0].min() + allp[:, 0].max())
    return [[(x - dx, y) for x, y in s] for s in out]


def strokes_from_g(strokes_g: Iterable[Sequence[Point]], geo: CellGeometry) -> List[Stroke]:
    """Штрихи .gfont -> штрихи проекта (fixed: уже обработаны)."""
    out = []
    for s in strokes_g:
        if len(s) < 1:
            continue
        p = geo.from_g(s)
        out.append(Stroke([(float(x), float(y)) for x, y in p], dot=False, fixed=True))
    return out
