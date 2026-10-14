"""TTF/OTF -> центральные линии штрихов.

Результат работы — GlyphShape в единицах шрифта (ось Y вверх):
    strokes: список (Nx2 массив, closed)
    dots:    список (cx, cy, r) — «точки», которые потом станут спиралями

Режимы:
    skeleton — растеризация заливки (правило nonzero), скелетизация, граф,
               чистка шипов, сборка штрихов с минимумом подъёмов пера;
    outline  — сами контуры как штрихи (для контурных и однолинейных шрифтов).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.morphology import skeletonize

Array = np.ndarray


@dataclass
class ExtractParams:
    em_px: int = 1000             # пикселей растра на em шрифта
    spur_ratio: float = 1.2       # шип короче spur_ratio * толщины штриха удаляется
    end_extend: float = 0.8       # продление концов на end_extend * (полутолщина)
    dot_aspect: float = 1.7       # сплошной компонент «круглее» этого считается точкой/пятном
    fill_spacing: float = 0.0     # шаг колец заливки крупных пятен, ед. шрифта (0 = upm/50)
    tiny_cap: float = 0.07        # компонент меньше этой доли заглавной — всегда точка
    hole_min_ratio: float = 0.0004  # дырки меньше (доля em^2) заливаются (шум)
    join_angle: float = 100.0     # макс. излом при склейке штрихов в общем узле, град.
    snap_px: float = 0.0          # склейка концов разных штрихов ближе, чем столько px


@dataclass
class GlyphShape:
    strokes: List[Tuple[Array, bool]] = field(default_factory=list)
    dots: List[Tuple[float, float, float]] = field(default_factory=list)
    fills: List[Array] = field(default_factory=list)   # заливка пятна (по индексу dots)
    stroke_width: float = 0.0     # медианная толщина штриха, ед. шрифта
    advance: float = 0.0          # ширина символа (hmtx), ед. шрифта

    @property
    def empty(self) -> bool:
        return not self.strokes and not self.dots


# --------------------------------------------------------------------------
# Контуры
# --------------------------------------------------------------------------

class FlattenPen(BasePen):
    """Перо, превращающее кривые Безье в плотные ломаные."""

    def __init__(self, glyphSet, tolerance: float):
        super().__init__(glyphSet)
        self.tol = tolerance
        self.contours: List[List[Tuple[float, float]]] = []
        self._cur: List[Tuple[float, float]] = []

    def _moveTo(self, pt):
        self._flush()
        self._cur = [pt]

    def _lineTo(self, pt):
        self._cur.append(pt)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur[-1]
        length = math.dist(p0, p1) + math.dist(p1, p2) + math.dist(p2, p3)
        n = max(2, int(length / self.tol))
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            x = mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0]
            y = mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]
            self._cur.append((x, y))

    def _qCurveToOne(self, p1, p2):
        p0 = self._cur[-1]
        length = math.dist(p0, p1) + math.dist(p1, p2)
        n = max(2, int(length / self.tol))
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
            y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
            self._cur.append((x, y))

    def _closePath(self):
        self._flush()

    def _endPath(self):
        self._flush()

    def _flush(self):
        if len(self._cur) >= 2:
            self.contours.append(self._cur)
        self._cur = []


class FontSource:
    """Открытый шрифт: cmap, контуры, метрики."""

    def __init__(self, path: str, font_number: int = 0):
        self.path = path
        self.font = TTFont(path, fontNumber=font_number, lazy=False)
        self.cmap: Dict[int, str] = self.font.getBestCmap() or {}
        self.glyphset = self.font.getGlyphSet()
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"] if "hmtx" in self.font else None

    def has(self, code: int) -> bool:
        return code in self.cmap

    def contours(self, code: int) -> List[Array]:
        name = self.cmap[code]
        pen = FlattenPen(self.glyphset, tolerance=self.upm / 400.0)
        self.glyphset[name].draw(pen)
        return [np.asarray(c, dtype=float) for c in pen.contours]

    def advance(self, code: int) -> float:
        if self.hmtx is None or code not in self.cmap:
            return 0.0
        return float(self.hmtx[self.cmap[code]][0])

    def bbox(self, code: int) -> Optional[Tuple[float, float, float, float]]:
        if code not in self.cmap:
            return None
        cs = self.contours(code)
        if not cs:
            return None
        allp = np.concatenate(cs)
        return (allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max())


def signed_area(c: Array) -> float:
    x, y = c[:, 0], c[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


# --------------------------------------------------------------------------
# Растр
# --------------------------------------------------------------------------

@dataclass
class Raster:
    mask: Array          # bool, [row, col], строки вниз
    k: float             # пикселей на единицу шрифта
    x0: float            # единицы шрифта, соответствующие col = pad
    y1: float            # единицы шрифта, соответствующие row = pad (верх)
    pad: int

    def to_font(self, rc: Array) -> Array:
        """(row, col) -> (x, y) в единицах шрифта."""
        rc = np.asarray(rc, dtype=float)
        x = (rc[..., 1] - self.pad) / self.k + self.x0
        y = self.y1 - (rc[..., 0] - self.pad) / self.k
        return np.stack([x, y], axis=-1)


def rasterize(contours: Sequence[Array], upm: int, em_px: int) -> Optional[Raster]:
    """Заливка по правилу nonzero: сумма вкладов контуров со знаком ориентации."""
    if not contours:
        return None
    k = em_px / float(upm)
    allp = np.concatenate(contours)
    x0, y0 = allp[:, 0].min(), allp[:, 1].min()
    x1, y1 = allp[:, 0].max(), allp[:, 1].max()
    pad = 6
    w = int(math.ceil((x1 - x0) * k)) + 2 * pad + 1
    h = int(math.ceil((y1 - y0) * k)) + 2 * pad + 1
    acc = np.zeros((h, w), dtype=np.int16)
    for c in contours:
        if len(c) < 3:
            continue
        a = signed_area(c)
        if a == 0:
            continue
        img = Image.new("L", (w, h), 0)
        pts = [((x - x0) * k + pad, (y1 - y) * k + pad) for x, y in c]
        ImageDraw.Draw(img).polygon(pts, fill=1, outline=1)
        acc += np.asarray(img, dtype=np.int16) * (1 if a > 0 else -1)
    mask = acc != 0
    return Raster(mask=mask, k=k, x0=x0, y1=y1, pad=pad)


def clean_mask(mask: Array, em_px: int, hole_min_ratio: float) -> Array:
    """Убрать мелкий мусор и залить микродырки (шум растеризации)."""
    min_speck = max(4, int(em_px * em_px * 0.00002))
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n:
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        for i, s in enumerate(sizes, 1):
            if s < min_speck:
                mask[lab == i] = False
    holes = ndimage.binary_fill_holes(mask) & ~mask
    lab, n = ndimage.label(holes)
    if n:
        sizes = ndimage.sum(holes, lab, range(1, n + 1))
        thr = hole_min_ratio * em_px * em_px
        for i, s in enumerate(sizes, 1):
            if s < thr:
                mask[lab == i] = True
    return mask


# --------------------------------------------------------------------------
# Граф скелета
# --------------------------------------------------------------------------

_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass
class Edge:
    a: int
    b: int
    pts: Array           # (N, 2) в пикселях (row, col)
    alive: bool = True
    closed: bool = False

    def length(self) -> float:
        if len(self.pts) < 2:
            return 0.0
        return float(np.sum(np.linalg.norm(np.diff(self.pts, axis=0), axis=1)))


class SkelGraph:
    def __init__(self):
        self.node_pos: Dict[int, Array] = {}
        self.edges: List[Edge] = []

    def add_node(self, pos) -> int:
        nid = len(self.node_pos)
        self.node_pos[nid] = np.asarray(pos, dtype=float)
        return nid

    def incident(self, n: int) -> List[int]:
        return [i for i, e in enumerate(self.edges) if e.alive and (e.a == n or e.b == n)]

    def degree(self, n: int) -> int:
        d = 0
        for e in self.edges:
            if e.alive:
                d += (e.a == n) + (e.b == n)
        return d


def build_graph(skel: Array) -> SkelGraph:
    h, w = skel.shape
    sk = np.pad(skel, 1)
    rows, cols = np.nonzero(sk)
    nbcount = ndimage.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8),
                               mode="constant") - sk.astype(np.uint8)
    is_node = sk & (nbcount != 2)
    # Кластеры узловых пикселей -> один узел
    lab, nlab = ndimage.label(is_node, structure=np.ones((3, 3)))
    g = SkelGraph()
    label_to_node: Dict[int, int] = {}
    if nlab:
        centers = ndimage.center_of_mass(is_node, lab, range(1, nlab + 1))
        for i, c in enumerate(centers, 1):
            label_to_node[i] = g.add_node(np.array(c) - 1.0)

    def nbrs(r, c):
        for dr, dc in _NB:
            if sk[r + dr, c + dc]:
                yield r + dr, c + dc

    visited = np.zeros_like(sk, dtype=bool)
    seen_pairs = set()
    node_pixels = list(zip(*np.nonzero(is_node)))
    for (r, c) in node_pixels:
        na = label_to_node[lab[r, c]]
        for (r2, c2) in nbrs(r, c):
            if is_node[r2, c2]:
                nb = label_to_node[lab[r2, c2]]
                if nb != na:
                    key = frozenset(((r, c), (r2, c2)))
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        pts = np.array([g.node_pos[na], g.node_pos[nb]])
                        g.edges.append(Edge(na, nb, pts))
                continue
            if visited[r2, c2]:
                continue
            path = [(r, c), (r2, c2)]
            visited[r2, c2] = True
            prev, cur = (r, c), (r2, c2)
            end_node = None
            while True:
                nxt = None
                for q in nbrs(*cur):
                    if q == prev:
                        continue
                    if is_node[q]:
                        # не возвращаемся в стартовый пиксель сразу же
                        if len(path) == 2 and q == path[0]:
                            continue
                        nxt = q
                        break
                    if not visited[q]:
                        nxt = q
                        break
                if nxt is None:
                    break
                path.append(nxt)
                if is_node[nxt]:
                    end_node = label_to_node[lab[nxt]]
                    break
                visited[nxt] = True
                prev, cur = cur, nxt
            pts = np.array(path, dtype=float) - 1.0
            pts[0] = g.node_pos[na]
            if end_node is None:
                # оборванная цепочка (не должна встречаться) — висячий конец
                end_node = g.add_node(pts[-1])
            else:
                pts[-1] = g.node_pos[end_node]
            g.edges.append(Edge(na, end_node, pts))

    # Чистые циклы без узлов (например «о»)
    rest = sk & ~is_node & ~visited
    for (r, c) in zip(*np.nonzero(rest)):
        if visited[r, c]:
            continue
        path = [(r, c)]
        visited[r, c] = True
        prev, cur = None, (r, c)
        while True:
            nxt = None
            for q in nbrs(*cur):
                if q != prev and not visited[q]:
                    nxt = q
                    break
            if nxt is None:
                break
            visited[nxt] = True
            path.append(nxt)
            prev, cur = cur, nxt
        pts = np.array(path, dtype=float) - 1.0
        if len(pts) < 3:
            continue
        n = g.add_node(pts[0])
        pts = np.vstack([pts, pts[:1]])
        g.edges.append(Edge(n, n, pts, closed=True))
    return g


def merge_degree2(g: SkelGraph) -> None:
    """Склеить рёбра в узлах степени 2 (ложные узлы от лесенок скелета)."""
    changed = True
    while changed:
        changed = False
        for n in list(g.node_pos):
            inc = g.incident(n)
            if len(inc) != 2 or g.degree(n) != 2:
                if len(inc) == 1:
                    e = g.edges[inc[0]]
                    if e.a == n and e.b == n and not e.closed:
                        e.closed = True
                continue
            e1, e2 = g.edges[inc[0]], g.edges[inc[1]]
            p1 = e1.pts if e1.b == n else e1.pts[::-1]
            o1 = e1.a if e1.b == n else e1.b
            p2 = e2.pts if e2.a == n else e2.pts[::-1]
            o2 = e2.b if e2.a == n else e2.a
            e1.alive = e2.alive = False
            ne = Edge(o1, o2, np.vstack([p1, p2[1:]]))
            if o1 == o2 and o1 == n:
                ne.closed = True
            g.edges.append(ne)
            changed = True


def prune_spurs(g: SkelGraph, dist: Array, ratio: float) -> None:
    """Удалить короткие шипы: ребро «конец — развилка» короче ratio * толщины."""
    for _ in range(6):
        removed = False
        for e in g.edges:
            if not e.alive or e.closed:
                continue
            da, db = g.degree(e.a), g.degree(e.b)
            if (da == 1 and db >= 3) or (db == 1 and da >= 3):
                jn = e.b if da == 1 else e.a
                r, c = np.round(g.node_pos[jn]).astype(int)
                r = min(max(r, 0), dist.shape[0] - 1)
                c = min(max(c, 0), dist.shape[1] - 1)
                width = 2.0 * max(dist[r, c], 1.0)
                if e.length() < ratio * width:
                    e.alive = False
                    removed = True
        if not removed:
            break
        merge_degree2(g)


def _width_at(dist: Array, pos: Array) -> float:
    r, c = np.round(pos).astype(int)
    r = min(max(r, 0), dist.shape[0] - 1)
    c = min(max(c, 0), dist.shape[1] - 1)
    return 2.0 * max(float(dist[r, c]), 1.0)


def contract_junctions(g: SkelGraph, dist: Array, ratio: float = 0.9) -> None:
    """Стянуть короткие рёбра «развилка — развилка» в один узел.

    Скелет пересечения (x, Ж, *) обычно даёт две близкие развилки степени 3
    вместо одной степени 4 — из-за этого штрих не может пройти «насквозь».
    """
    changed = True
    while changed:
        changed = False
        for e in g.edges:
            if not e.alive or e.closed or e.a == e.b:
                continue
            if g.degree(e.a) < 3 or g.degree(e.b) < 3:
                continue
            w = max(_width_at(dist, g.node_pos[e.a]), _width_at(dist, g.node_pos[e.b]))
            if e.length() >= ratio * w:
                continue
            keep, gone = e.a, e.b
            newpos = 0.5 * (g.node_pos[keep] + g.node_pos[gone])
            e.alive = False
            g.node_pos[keep] = newpos
            for o in g.edges:
                if not o.alive:
                    continue
                if o.a == gone:
                    o.a = keep
                if o.b == gone:
                    o.b = keep
                if o.a == keep:
                    o.pts = np.vstack([newpos, o.pts[1:]])
                if o.b == keep:
                    o.pts = np.vstack([o.pts[:-1], newpos])
            changed = True
            break


def _end_direction(pts: Array, at_start: bool, dist: float) -> Array:
    """Единичный вектор, направленный наружу из ребра на его конце."""
    seq = pts if at_start else pts[::-1]
    end = seq[0]
    acc = 0.0
    ref = seq[-1]
    for i in range(1, len(seq)):
        acc += float(np.linalg.norm(seq[i] - seq[i - 1]))
        if acc >= dist:
            ref = seq[i]
            break
    v = end - ref
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else np.array([0.0, 0.0])


def extend_ends(g: SkelGraph, dist: Array, factor: float) -> None:
    """Продлить висячие концы на factor * локальную полутолщину."""
    if factor <= 0:
        return
    for e in g.edges:
        if not e.alive or e.closed:
            continue
        for at_start, node in ((True, e.a), (False, e.b)):
            if g.degree(node) != 1:
                continue
            p = e.pts[0] if at_start else e.pts[-1]
            r, c = np.round(p).astype(int)
            r = min(max(r, 0), dist.shape[0] - 1)
            c = min(max(c, 0), dist.shape[1] - 1)
            ext = factor * float(dist[r, c])
            if ext < 1.0:
                continue
            d = _end_direction(e.pts, at_start, max(4.0, 2.0 * dist[r, c]))
            newp = p + d * ext
            if at_start:
                e.pts = np.vstack([newp, e.pts])
            else:
                e.pts = np.vstack([e.pts, newp])
            g.node_pos[node] = newp


# --------------------------------------------------------------------------
# Сборка штрихов
# --------------------------------------------------------------------------

def _angle(u: Array, v: Array) -> float:
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return 90.0
    c = float(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))
    return math.degrees(math.acos(c))


def assemble_strokes(g: SkelGraph, dir_dist: float, join_angle: float
                     ) -> List[Tuple[Array, bool, int, int]]:
    """Покрыть все рёбра путями. Возвращает (pts, closed, start_node, end_node)."""
    alive = [i for i, e in enumerate(g.edges) if e.alive]
    used = set()
    inc: Dict[int, List[int]] = {}
    for i in alive:
        e = g.edges[i]
        inc.setdefault(e.a, []).append(i)
        if e.b != e.a:
            inc.setdefault(e.b, []).append(i)
        else:
            inc.setdefault(e.a, [])

    def unused_deg(n):
        d = 0
        for i in inc.get(n, []):
            if i not in used:
                e = g.edges[i]
                d += 2 if e.a == e.b else 1
        return d

    strokes = []
    while len(used) < len(alive):
        # старт: висячие концы, потом нечётные узлы, потом любые; сверху-слева
        cands = [n for n in inc if unused_deg(n) > 0]
        def score(n):
            d = unused_deg(n)
            pri = 0 if d == 1 else (1 if d % 2 == 1 else 2)
            r, c = g.node_pos[n]
            return (pri, c + 0.5 * r)
        cur = min(cands, key=score)
        path: List[Array] = []
        start_node = cur
        incoming: Optional[Array] = None
        closed_flag = False
        while True:
            options = [i for i in inc.get(cur, []) if i not in used]
            if not options:
                break
            best, best_cost, best_pts = None, None, None
            for i in options:
                e = g.edges[i]
                variants = []
                if e.a == cur:
                    variants.append(e.pts)
                if e.b == cur:
                    variants.append(e.pts[::-1])
                for pts in variants:
                    out_dir = -_end_direction(pts, True, dir_dist)
                    cost = 0.0 if incoming is None else _angle(incoming, out_dir)
                    if best_cost is None or cost < best_cost:
                        best, best_cost, best_pts = i, cost, pts
            if incoming is not None and path and best_cost > 150.0:
                # почти разворот назад — лучше поднять перо
                break
            used.add(best)
            e = g.edges[best]
            if e.closed and not path:
                closed_flag = True
            path.append(best_pts if not path else best_pts[1:])
            cur = e.b if (e.a == cur and best_pts is e.pts) else e.a
            if e.a == e.b:
                cur = e.a
            incoming = _end_direction(best_pts, False, dir_dist)
            if e.closed:
                break
        if path:
            pts = np.vstack(path)
            closed = closed_flag or (cur == start_node and len(pts) > 3)
            strokes.append((pts, closed, start_node, cur))
    return _join_strokes(strokes, dir_dist, join_angle)


def _join_strokes(strokes, dir_dist, join_angle):
    """Склеить открытые штрихи, сходящиеся в одном узле, если излом невелик."""
    strokes = [list(s) for s in strokes]
    changed = True
    while changed:
        changed = False
        for i in range(len(strokes)):
            if strokes[i] is None or strokes[i][1]:
                continue
            for j in range(len(strokes)):
                if i == j or strokes[j] is None or strokes[j][1]:
                    continue
                a, b = strokes[i], strokes[j]
                for a_end in (True, False):          # True: используем конец a
                    for b_start in (True, False):    # True: используем начало b
                        na = a[3] if a_end else a[2]
                        nb = b[2] if b_start else b[3]
                        if na != nb:
                            continue
                        pa = a[0] if a_end else a[0][::-1]
                        pb = b[0] if b_start else b[0][::-1]
                        din = _end_direction(pa, False, dir_dist)
                        dout = -_end_direction(pb, True, dir_dist)
                        if _angle(din, dout) <= join_angle:
                            s_node = a[2] if a_end else a[3]
                            e_node = b[3] if b_start else b[2]
                            pts = np.vstack([pa, pb[1:]])
                            strokes[i] = [pts, s_node == e_node, s_node, e_node]
                            strokes[j] = None
                            changed = True
                            break
                    if changed:
                        break
                if changed:
                    break
            if changed:
                break
    return [tuple(s) for s in strokes if s is not None]


# --------------------------------------------------------------------------
# Основная функция
# --------------------------------------------------------------------------

def _is_dot(comp_mask: Array, dist: Array, cap_px: float, p: ExtractParams) -> bool:
    rows, cols = np.nonzero(comp_mask)
    h = rows.max() - rows.min() + 1
    w = cols.max() - cols.min() + 1
    big = max(h, w)
    if big < p.tiny_cap * cap_px:
        return True
    r = float(dist[comp_mask].max())
    if r <= 0:
        return True
    has_hole = bool((ndimage.binary_fill_holes(comp_mask) & ~comp_mask).any())
    if has_hole:
        return False
    return big / (2.0 * r) < p.dot_aspect


def fill_rings(comp_mask: Array, spacing_px: float) -> Optional[Array]:
    """Заливка пятна: концентрические кольца (изолинии расстояния до края),
    соединённые в один путь снаружи внутрь."""
    from skimage.measure import find_contours
    d = ndimage.distance_transform_edt(np.pad(comp_mask, 1))
    rmax = float(d.max())
    if rmax < spacing_px * 0.75:
        return None
    path: List[Array] = []
    level = spacing_px * 0.5
    while level < rmax - 0.25 * spacing_px:
        rings = find_contours(d, level)
        if not rings:
            break
        ring = max(rings, key=len)[:-1]
        if path:
            j = int(np.argmin(np.linalg.norm(ring - path[-1][-1], axis=1)))
            ring = np.vstack([ring[j:], ring[:j]])
        ring = np.vstack([ring, ring[:1]])
        path.append(ring)
        level += spacing_px
    if not path:
        return None
    pts = np.vstack(path) - 1.0
    return pts


def extract_skeleton(contours: Sequence[Array], upm: int, cap_units: float,
                     p: ExtractParams) -> GlyphShape:
    shape = GlyphShape()
    ras = rasterize(contours, upm, p.em_px)
    if ras is None:
        return shape
    mask = clean_mask(ras.mask, p.em_px, p.hole_min_ratio)
    if not mask.any():
        return shape
    dist = ndimage.distance_transform_edt(mask)
    cap_px = cap_units * ras.k
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    stroke_mask = np.zeros_like(mask)
    for i in range(1, n + 1):
        comp = lab == i
        if _is_dot(comp, dist, cap_px, p):
            rows, cols = np.nonzero(comp)
            cy, cx = rows.mean(), cols.mean()
            rad = math.sqrt(comp.sum() / math.pi)
            fx, fy = ras.to_font(np.array([cy, cx]))
            shape.dots.append((float(fx), float(fy), rad / ras.k))
            spacing = (p.fill_spacing or upm / 50.0) * ras.k
            r0, c0 = rows.min(), cols.min()
            sub = comp[r0:rows.max() + 1, c0:cols.max() + 1]
            rings = fill_rings(sub, spacing)
            shape.fills.append(ras.to_font(rings + [r0, c0]) if rings is not None else None)
        else:
            stroke_mask |= comp
    if stroke_mask.any():
        skel = skeletonize(stroke_mask)
        widths = 2.0 * dist[skel]
        shape.stroke_width = float(np.median(widths)) / ras.k if widths.size else 0.0
        g = build_graph(skel)
        merge_degree2(g)
        prune_spurs(g, dist, p.spur_ratio)
        merge_degree2(g)
        contract_junctions(g, dist)
        merge_degree2(g)
        extend_ends(g, dist, p.end_extend)
        med_w = float(np.median(widths)) if widths.size else 4.0
        dir_dist = max(4.0, 1.5 * med_w)
        for pts, closed, _, _ in assemble_strokes(g, dir_dist, p.join_angle):
            if len(pts) < 2:
                continue
            shape.strokes.append((ras.to_font(pts), bool(closed)))
        if p.snap_px > 0:
            shape.strokes = snap_strokes(shape.strokes, p.snap_px / ras.k)
    return shape


def snap_strokes(strokes, tol):
    """Склеить открытые штрихи, концы которых ближе tol (ед. шрифта)."""
    strokes = [list(s) for s in strokes]
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(strokes):
            if a is None or a[1]:
                continue
            for j, b in enumerate(strokes):
                if j == i or b is None or b[1]:
                    continue
                for pa in (a[0], a[0][::-1]):
                    for pb in (b[0], b[0][::-1]):
                        if np.linalg.norm(pa[-1] - pb[0]) <= tol:
                            strokes[i] = [np.vstack([pa, pb]), False]
                            strokes[j] = None
                            changed = True
                            break
                    if changed:
                        break
                if changed:
                    break
            if changed:
                break
    return [(s[0], s[1]) for s in strokes if s is not None]


def extract_outline(contours: Sequence[Array]) -> GlyphShape:
    """Контуры как штрихи. Контур «туда-обратно» (однолинейный шрифт) -> открытый штрих."""
    shape = GlyphShape()
    for c in contours:
        if len(c) < 2:
            continue
        per = float(np.sum(np.linalg.norm(np.diff(np.vstack([c, c[:1]]), axis=0), axis=1)))
        if per <= 0:
            continue
        area = abs(signed_area(c)) if len(c) >= 3 else 0.0
        if area / (per * per) < 0.002:
            # вырожденный контур: берём половину пути
            seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
            cum = np.concatenate([[0], np.cumsum(seg)])
            half = int(np.searchsorted(cum, per / 2.0))
            shape.strokes.append((c[:max(2, half + 1)], False))
        else:
            shape.strokes.append((np.vstack([c, c[:1]]), True))
    return shape


def is_single_line_font(src: FontSource, sample: str = "HnoаиЕ") -> bool:
    """Эвристика для --mode auto: шрифт из вырожденных контуров (однолинейный)."""
    deg = tot = 0
    for ch in sample:
        if not src.has(ord(ch)):
            continue
        for c in src.contours(ord(ch)):
            per = float(np.sum(np.linalg.norm(np.diff(np.vstack([c, c[:1]]), axis=0), axis=1)))
            if per <= 0:
                continue
            tot += 1
            area = abs(signed_area(c)) if len(c) >= 3 else 0.0
            if area / (per * per) < 0.002:
                deg += 1
    return tot > 0 and deg / tot > 0.5


def extract_glyph(src: FontSource, code: int, mode: str, cap_units: float,
                  p: ExtractParams) -> GlyphShape:
    contours = src.contours(code)
    if mode == "outline":
        shape = extract_outline(contours)
    else:
        shape = extract_skeleton(contours, src.upm, cap_units, p)
    shape.advance = src.advance(code)
    return shape
