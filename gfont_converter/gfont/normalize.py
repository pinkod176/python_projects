"""Перевод штрихов из единиц шрифта в систему координат .gfont.

Система координат .gfont (измерено на blood8真迹4):
    ось Y направлена вниз; базовая линия около -85;
    высота заглавных около 315, строчных около 220, выносные вверх ~365, вниз ~150;
    X центрирован по ограничивающему прямоугольнику глифа;
    шаг между точками около 27, обычно ~20 точек на глиф.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .extract import FontSource, GlyphShape

Point = Tuple[float, float]


@dataclass
class TargetMetrics:
    baseline: float = -85.0     # Y базовой линии в .gfont
    cap_height: float = 315.0   # высота заглавных в единицах .gfont
    x_height: Optional[float] = None   # если задано и size_by=xheight — масштаб по ней
    size_by: str = "cap"        # cap | xheight
    scale: float = 1.0          # ручной множитель
    slant_deg: float = 0.0      # наклон вправо, градусы
    spacing: float = 1.0        # множитель ширины по X (грубая подгонка интервала)
    step: float = 25.0          # шаг передискретизации
    smooth: float = 3.0         # сигма гауссова сглаживания, ед. .gfont
    corner_deg: float = 40.0    # излом больше этого сохраняется как угол
    dot_radius: float = 6.0     # минимальный радиус спирали для «точки»
    fill_spacing: float = 9.0   # шаг витков при заливке крупных пятен (● ■)
    side_anchors: bool = False  # экспериментально: одиночные move-to на краях advance


@dataclass
class FontMetrics:
    upm: int
    cap: float
    xheight: float
    ascender: float
    descender: float


def measure_font(src: FontSource) -> FontMetrics:
    os2 = src.font["OS/2"] if "OS/2" in src.font else None

    def from_glyph(chars: str, top: bool) -> Optional[float]:
        vals = []
        for ch in chars:
            bb = src.bbox(ord(ch))
            if bb:
                vals.append(bb[3] if top else bb[1])
        return float(np.median(vals)) if vals else None

    cap = getattr(os2, "sCapHeight", 0) if os2 is not None else 0
    if not cap or cap <= 0:
        cap = from_glyph("HIEТН", True) or 0.7 * src.upm
    xh = getattr(os2, "sxHeight", 0) if os2 is not None else 0
    if not xh or xh <= 0:
        xh = from_glyph("xzvnи", True) or 0.5 * src.upm
    asc = from_glyph("bdhklб", True) or 0.75 * src.upm
    desc = from_glyph("pqgyру", False) or -0.2 * src.upm
    return FontMetrics(src.upm, float(cap), float(xh), float(asc), float(desc))


def font_scale(fm: FontMetrics, tm: TargetMetrics) -> float:
    if tm.size_by == "xheight":
        target = tm.x_height if tm.x_height else 220.0
        s = target / fm.xheight
    else:
        s = tm.cap_height / fm.cap
    return s * tm.scale


# --------------------------------------------------------------------------
# Геометрия ломаных
# --------------------------------------------------------------------------

def polyline_length(p: np.ndarray) -> float:
    if len(p) < 2:
        return 0.0
    return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))


def rdp(points: np.ndarray, eps: float) -> List[int]:
    """Рамер-Дуглас-Пекер; возвращает индексы сохранённых точек."""
    n = len(points)
    if n < 3:
        return list(range(n))
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = points[i], points[j]
        ab = b - a
        L = np.hypot(*ab)
        seg = points[i + 1:j]
        if L < 1e-12:
            d = np.hypot(*(seg - a).T)
        else:
            d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return list(np.nonzero(keep)[0])


def _corner_indices(p: np.ndarray, closed: bool, corner_deg: float, eps: float) -> List[int]:
    idx = rdp(p, eps)
    corners = []
    for t in range(1, len(idx) - 1):
        a, b, c = p[idx[t - 1]], p[idx[t]], p[idx[t + 1]]
        u, v = b - a, c - b
        nu, nv = np.hypot(*u), np.hypot(*v)
        if nu < 1e-9 or nv < 1e-9:
            continue
        ang = math.degrees(math.acos(float(np.clip(np.dot(u, v) / (nu * nv), -1, 1))))
        if ang >= corner_deg:
            corners.append(idx[t])
    return corners


def _smooth_open(p: np.ndarray, sigma_units: float) -> np.ndarray:
    """Гауссово сглаживание с закреплёнными концами."""
    if len(p) < 4 or sigma_units <= 0:
        return p
    L = polyline_length(p)
    if L <= 0:
        return p
    spacing = L / (len(p) - 1)
    sig = sigma_units / max(spacing, 1e-6)
    if sig < 0.3:
        return p
    t = np.linspace(0, 1, len(p))[:, None]
    base = p[0] + (p[-1] - p[0]) * t
    d = p - base
    ds = gaussian_filter1d(d, sig, axis=0, mode="constant", cval=0.0)
    return base + ds


def _smooth_closed(p: np.ndarray, sigma_units: float) -> np.ndarray:
    q = p[:-1] if np.allclose(p[0], p[-1]) else p
    if len(q) < 4 or sigma_units <= 0:
        return p
    spacing = polyline_length(np.vstack([q, q[:1]])) / len(q)
    sig = sigma_units / max(spacing, 1e-6)
    qs = gaussian_filter1d(q, sig, axis=0, mode="wrap")
    return np.vstack([qs, qs[:1]])


def resample(p: np.ndarray, step: float, min_pts: int = 2) -> np.ndarray:
    L = polyline_length(p)
    if L <= 1e-9:
        return p[:1].repeat(min_pts, axis=0)
    n = max(min_pts - 1, int(round(L / step)))
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.linspace(0, L, n + 1)
    x = np.interp(t, cum, p[:, 0])
    y = np.interp(t, cum, p[:, 1])
    return np.stack([x, y], axis=1)


def refine_stroke(p: np.ndarray, closed: bool, tm: TargetMetrics) -> np.ndarray:
    """Углы (RDP) + сглаживание кусков между углами + равномерная передискретизация."""
    p = np.asarray(p, dtype=float)
    if len(p) < 2:
        return p
    if closed and not np.allclose(p[0], p[-1]):
        p = np.vstack([p, p[:1]])
    eps = max(1.0, tm.step * 0.08)
    corners = _corner_indices(p, closed, tm.corner_deg, eps)
    if closed and corners:
        # начинаем замкнутый контур с угла, дальше как открытый
        k = corners[0]
        p = np.vstack([p[k:-1], p[:k + 1]])
        corners = [c - k if c >= k else c + len(p) - 1 - k for c in corners[1:]]
        corners = sorted(c for c in corners if 0 < c < len(p) - 1)
        closed_smooth = False
    else:
        closed_smooth = closed
    if closed_smooth:
        p = _smooth_closed(p, tm.smooth)
        L = polyline_length(p)
        q = resample(p, tm.step, min_pts=max(5, int(round(L / tm.step)) + 1))
        q[-1] = q[0]
        return q
    cuts = [0] + corners + [len(p) - 1]
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        seg = p[a:b + 1]
        seg = _smooth_open(seg, tm.smooth)
        L = polyline_length(seg)
        r = resample(seg, tm.step, min_pts=2 if L < tm.step * 1.5 else 3)
        out.append(r if not out else r[1:])
    return np.vstack(out)


def spiral(cx: float, cy: float, r_blob: float, tm: TargetMetrics) -> np.ndarray:
    """Спираль на месте «точки»: маленькая — 6 точек, крупное пятно — заливка витками."""
    r_out = max(tm.dot_radius, 0.75 * r_blob)
    if r_out <= 3.5 * tm.dot_radius:
        n = 6
        ang = np.linspace(0, 2 * math.pi * 1.15, n)
        rad = np.linspace(0.2 * r_out, r_out, n)
    else:
        turns = max(1.25, r_out / tm.fill_spacing)
        total = 2 * math.pi * turns
        # шаг вдоль спирали около step/2
        approx_len = math.pi * r_out * turns
        n = max(8, int(approx_len / (tm.step * 0.5)))
        ang = np.linspace(0, total, n)
        rad = r_out * np.sqrt(np.linspace(0.02, 1.0, n))
    x = cx + rad * np.cos(ang)
    y = cy - rad * np.sin(ang)
    return np.stack([x, y], axis=1)


# --------------------------------------------------------------------------
# Глиф целиком
# --------------------------------------------------------------------------

def _variation(rng: np.random.Generator, amount: float):
    return dict(
        slant=math.radians(rng.normal(0, 2.0) * amount),
        scale=1.0 + rng.normal(0, 0.025) * amount,
        rot=math.radians(rng.normal(0, 1.0) * amount),
        dy=rng.normal(0, 2.0) * amount,
        jitter=1.2 * amount,
    )


def _smooth_noise(rng, n: int, amp: float) -> np.ndarray:
    if amp <= 0 or n == 0:
        return np.zeros((n, 2))
    z = rng.normal(0, 1, size=(n, 2))
    z = gaussian_filter1d(z, max(1.0, n / 6.0), axis=0, mode="nearest")
    s = z.std() or 1.0
    return z / s * amp


def place_glyph(shape: GlyphShape, s: float, tm: TargetMetrics,
                variation: float = 0.0, rng: Optional[np.random.Generator] = None,
                info: Optional[dict] = None) -> List[List[Point]]:
    """GlyphShape (ед. шрифта) -> штрихи .gfont (Y вниз, X по центру bbox)."""
    var = _variation(rng, variation) if (variation > 0 and rng is not None) else None
    slant = math.tan(math.radians(tm.slant_deg) + (var["slant"] if var else 0.0))
    gs = s * (var["scale"] if var else 1.0)

    def tf(pts: np.ndarray) -> np.ndarray:
        x = pts[:, 0] * gs * tm.spacing
        h = pts[:, 1] * gs                       # высота над базовой линией
        if var and var["rot"]:
            c, sn = math.cos(var["rot"]), math.sin(var["rot"])
            x, h = x * c - h * sn, x * sn + h * c
        x = x + h * slant
        y = tm.baseline - h + (var["dy"] if var else 0.0)
        return np.stack([x, y], axis=1)

    strokes: List[np.ndarray] = []
    for pts, closed in shape.strokes:
        q = tf(np.asarray(pts, dtype=float))
        if var and var["jitter"] > 0:
            q = q + _smooth_noise(rng, len(q), var["jitter"])
            if closed:
                q[-1] = q[0]
        q = refine_stroke(q, closed, tm)
        if len(q) >= 2:
            strokes.append(q)
    fills = shape.fills if len(shape.fills) == len(shape.dots) else [None] * len(shape.dots)
    for (cx, cy, r), fill in zip(shape.dots, fills):
        if fill is not None and r * gs > 3.5 * tm.dot_radius:
            # крупное пятно (● ■ •): кольца по форме пятна
            q = resample(tf(np.asarray(fill, dtype=float)), tm.step * 0.6, min_pts=2)
            strokes.append(q)
        else:
            c = tf(np.array([[cx, cy]]))[0]
            strokes.append(spiral(c[0], c[1], r * gs, tm))

    anchors: List[np.ndarray] = []
    if tm.side_anchors and shape.advance > 0:
        lo = tf(np.array([[0.0, 0.0]]))[0]
        hi = tf(np.array([[shape.advance, 0.0]]))[0]
        anchors = [lo[None, :], hi[None, :]]

    if not strokes:
        return []
    allp = np.vstack(strokes + anchors)
    cx = 0.5 * (allp[:, 0].min() + allp[:, 0].max())
    if info is not None:
        info["cx"] = float(cx)
    out = []
    for q in _order_strokes(strokes):
        q = q.copy()
        q[:, 0] -= cx
        out.append([(float(x), float(y)) for x, y in q])
    for a in anchors:
        out.append([(float(a[0, 0] - cx), float(a[0, 1]))])
    return out


def _order_strokes(strokes: List[np.ndarray]) -> List[np.ndarray]:
    """Направление (сверху вниз / слева направо) и порядок штрихов слева направо."""
    fixed = []
    for q in strokes:
        closed = len(q) > 2 and np.allclose(q[0], q[-1])
        if not closed:
            d = q[-1] - q[0]
            if abs(d[1]) > abs(d[0]):
                if d[1] < 0:            # конец выше начала -> разворачиваем
                    q = q[::-1]
            elif d[0] < 0:
                q = q[::-1]
        fixed.append(q)
    return sorted(fixed, key=lambda q: (round(float(q[:, 0].min()) / 60.0), float(q[:, 1].min())))


def place_outline(contours, s: float, tm: TargetMetrics, cx: float) -> List[np.ndarray]:
    """Контуры исходного шрифта в координатах .gfont (для сравнения в предпросмотре)."""
    slant = math.tan(math.radians(tm.slant_deg))
    out = []
    for c in contours:
        c = np.asarray(c, dtype=float)
        x = c[:, 0] * s * tm.spacing
        h = c[:, 1] * s
        out.append(np.stack([x + h * slant - cx, tm.baseline - h], axis=1))
    return out
