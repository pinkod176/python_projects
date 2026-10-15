"""Заполнение недостающих символов (без Qt).

(а) из шрифта TTF/OTF — через движок конвертера (FontSession), с подгонкой размера
    под почерк: высота заглавных/строчных шрифта приводится к нарисованной пользователем;
(б) из похожих уже нарисованных символов: одинаковые по виду буквы кириллицы и латиницы
    (а↔a, Р↔P…), ‑ − – — из дефиса, ё/Ё = е/Е + две точки, й/Й = и/И + дужка, № = N + o;
(в) оставить пустыми (ничего не делать).
Результат — словарь «код -> Candidate» для предварительного просмотра; в проект
кандидаты попадают, только когда пользователь их подтвердит.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .charsets import CAP_LETTERS, XHEIGHT_LETTERS
from .geometry import CellGeometry
from .project import DRAWN, GlyphEntry, Project, Stroke
from .strokes import glyph_raw_g, size_stats, strokes_from_g


@dataclass
class Candidate:
    strokes: List[Stroke]      # единицы холста
    how: str                   # понятное описание («из е + две точки», «из шрифта Arial»)
    source: str                # similar | font


# ---------------------------------------------------------------- геометрия
def _bbox(strokes: List[Stroke]) -> Optional[Tuple[float, float, float, float]]:
    pts = [p for s in strokes for p in s.pts]
    if not pts:
        return None
    a = np.asarray(pts, dtype=float)
    return float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())


def _map(strokes: List[Stroke], fn) -> List[Stroke]:
    return [Stroke([fn(x, y) for x, y in s.pts], s.dot, s.fixed) for s in strokes]


def _stretch_x(strokes: List[Stroke], f: float) -> List[Stroke]:
    b = _bbox(strokes)
    if b is None:
        return []
    cx = 0.5 * (b[0] + b[2])
    return _map(strokes, lambda x, y: (cx + (x - cx) * f, y))


def _two_dots(b, geo: CellGeometry) -> List[Stroke]:
    x0, y0, x1, _ = b
    w = max(x1 - x0, 0.3 * geo.cap)
    cx = 0.5 * (x0 + x1)
    y = y0 - 0.2 * geo.cap
    return [Stroke([(cx - 0.2 * w, y)], dot=True), Stroke([(cx + 0.2 * w, y)], dot=True)]


def _breve(b, geo: CellGeometry) -> List[Stroke]:
    x0, y0, x1, _ = b
    w = max(x1 - x0, 0.3 * geo.cap)
    cx = 0.5 * (x0 + x1)
    top = y0 - 0.26 * geo.cap
    depth = 0.11 * geo.cap
    t = np.linspace(-1.0, 1.0, 11)
    pts = [(cx + 0.28 * w * v, top + depth * (1 - v * v)) for v in t]
    return [Stroke(pts)]


def _numero(n: List[Stroke], o: List[Stroke], geo: CellGeometry) -> List[Stroke]:
    bn, bo = _bbox(n), _bbox(o)
    s = 0.5 * geo.cap / max(bo[3] - bo[1], 1.0)
    ox0 = bn[2] + 0.08 * geo.cap
    oy0 = geo.capline
    small = _map(o, lambda x, y: (ox0 + (x - bo[0]) * s, oy0 + (y - bo[1]) * s))
    sb = _bbox(small)
    uy = sb[3] + 0.12 * geo.cap
    line = Stroke([(sb[0], uy), (sb[2], uy)])
    out = n + small + [line]
    # всё вместе — по центру клетки
    b = _bbox(out)
    dx = geo.cx - 0.5 * (b[0] + b[2])
    return _map(out, lambda x, y: (x + dx, y))


# ---------------------------------------------------------------- (б) похожие
HOMOGLYPHS = [("а", "a"), ("е", "e"), ("о", "o"), ("р", "p"), ("с", "c"), ("у", "y"),
              ("х", "x"), ("А", "A"), ("В", "B"), ("Е", "E"), ("К", "K"), ("М", "M"),
              ("Н", "H"), ("О", "O"), ("Р", "P"), ("С", "C"), ("Т", "T"), ("Х", "X")]

COPIES = {  # код -> (из чего, растяжение по X, описание)
    0x2011: ("-", 1.0, "копия дефиса"),
    0x2010: ("-", 1.0, "копия дефиса"),
    0x2212: ("-", 1.15, "дефис чуть длиннее"),
    0x2013: ("-", 1.6, "дефис, растянутый в 1.6 раза"),
    0x2014: ("-", 2.6, "дефис, растянутый в 2.6 раза"),
    ord("’"): ("'", 1.0, "копия апострофа"),
    ord("‘"): ("'", 1.0, "копия апострофа"),
}


def similar_candidates(project: Project, codes: Iterable[int]) -> Dict[int, Candidate]:
    geo = project.geometry()

    def drawn(ch: str) -> Optional[List[Stroke]]:
        e = project.glyphs.get(ord(ch))
        return [s.copy() for s in e.strokes] if e and e.has_drawing() else None

    out: Dict[int, Candidate] = {}
    for code in codes:
        e = project.glyphs.get(code)
        if e and e.has_drawing():
            continue
        ch = chr(code)
        cand = None
        for a, b in HOMOGLYPHS:
            if ch in (a, b):
                other = b if ch == a else a
                src = drawn(other)
                if src:
                    script = "латинской" if other == b else "русской"
                    cand = Candidate(src, f"как {script} «{other}»", "similar")
                break
        if cand is None and code in COPIES:
            base, f, how = COPIES[code]
            src = drawn(base)
            if src:
                cand = Candidate(_stretch_x(src, f), how, "similar")
        if cand is None and ch in "ёЁйЙ":
            base = {"ё": "е", "Ё": "Е", "й": "и", "Й": "И"}[ch]
            src = drawn(base)
            if src:
                b = _bbox(src)
                extra = _two_dots(b, geo) if ch in "ёЁ" else _breve(b, geo)
                how = "две точки" if ch in "ёЁ" else "дужка"
                cand = Candidate(src + extra, f"«{base}» + {how}", "similar")
        if cand is None and ch == "№":
            n = drawn("N") or drawn("И")
            o = drawn("o") or drawn("о")
            if n and o:
                cand = Candidate(_numero(n, o, geo), "«N» + маленькая «o» с чертой", "similar")
        if cand is not None:
            out[code] = cand
    return out


# ---------------------------------------------------------------- (а) из шрифта
def user_size_factor(project: Project) -> float:
    """Во сколько раз почерк пользователя крупнее разметки (1 — ровно по линиям)."""
    geo = project.geometry()
    glyphs = {}
    for c, e in project.glyphs.items():
        if e.has_drawing() and e.source in ("", "user") and (chr(c) in XHEIGHT_LETTERS
                                                             or chr(c) in CAP_LETTERS):
            glyphs[c] = glyph_raw_g(e.strokes, geo, 0.0, 1.0)
    xh, cap = size_stats(glyphs, geo.tm)
    if cap:
        f = cap / (geo.tm.cap_height * geo.tm.scale)
    elif xh:
        f = xh / (geo.xheight * geo.k)
    else:
        return 1.0
    return float(min(1.4, max(0.7, f)))


def font_candidates(font_path: str, codes: Iterable[int], project: Project, *,
                    fit_to_user: bool = True, progress: Optional[Callable[[int, int], None]] = None,
                    cancel: Optional[Callable[[], bool]] = None) -> Dict[int, Candidate]:
    """Глифы шрифта через конвертер (тот же код, что в основном режиме)."""
    from gfont.errors import Cancelled
    from gfont.session import FontSession, UiParams

    session = FontSession(font_path)
    geo = project.geometry()
    f = user_size_factor(project) if fit_to_user else 1.0
    p = UiParams(scale=f, smooth=3.0, density=project.settings.density)
    codes = [c for c in codes if session.source_code(c) is not None]
    out: Dict[int, Candidate] = {}
    for i, code in enumerate(codes):
        if cancel is not None and cancel():
            raise Cancelled()
        r = session.glyph(code, p)
        if r.strokes:
            how = f"из шрифта {session.family}" + (f", размер ×{f:.2f} под почерк" if abs(f - 1) > 0.01 else "")
            out[code] = Candidate(strokes_from_g(r.strokes, geo), how, "font")
        if progress:
            progress(i + 1, len(codes))
    return out


def apply_candidates(project: Project, cands: Dict[int, Candidate]) -> None:
    for code, c in cands.items():
        e = project.entry(code)
        variants = [c.strokes] + e.variants[1:] if e.variants else [c.strokes]
        project.glyphs[code] = GlyphEntry(variants, DRAWN, c.source)
    if cands:
        project.dirty = True
