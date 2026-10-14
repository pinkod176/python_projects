"""Калибровочный .gfont: геометрические глифы, по которым видно, как приложение
считает интервал, толщину пера и положение на строке."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from .format import GFont, read_gfont
from .normalize import TargetMetrics

Point = Tuple[float, float]


def _rect(x0, y0, x1, y1) -> List[Point]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def _ellipse(cx, cy, rx, ry, n=24) -> List[Point]:
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy - ry * math.sin(2 * math.pi * i / n))
            for i in range(n + 1)]


def _line(x0, y0, x1, y1, step=25.0) -> List[Point]:
    n = max(1, int(round(math.hypot(x1 - x0, y1 - y0) / step)))
    return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n + 1)]


def calibration_glyphs(tm: TargetMetrics, asc: float = 365.0, desc: float = 150.0
                       ) -> Dict[str, Tuple[List[List[Point]], str]]:
    B = tm.baseline
    CAP = tm.cap_height
    XH = tm.x_height or 220.0
    top_cap, top_x, top_a, bot_d = B - CAP, B - XH, B - asc, B + desc
    g: Dict[str, Tuple[List[List[Point]], str]] = {}

    g["I"] = ([_line(0, top_cap, 0, B)], "вертикаль: базовая линия -> высота заглавной")
    g["|"] = ([_line(0, top_a, 0, bot_d)], "вертикаль: верхний выносной -> нижний выносной")
    g["H"] = ([_line(-80, top_cap, -80, B), _line(-80, B - CAP / 2, 80, B - CAP / 2),
               _line(80, top_cap, 80, B)], "H ширина 160, высота заглавной")
    g["x"] = ([_line(-70, top_x, 70, B), _line(70, top_x, -70, B)], "x ширина 140, высота строчной")
    g["o"] = ([_ellipse(0, B - XH / 2, 65, XH / 2)], "o: эллипс 130 x высота строчной")
    for d in range(10):
        w = 20 + 40 * d
        g[str(d)] = ([_rect(-w / 2, top_cap, w / 2, B)],
                     f"прямоугольник шириной {w}: зависит ли интервал от ширины глифа")
    g["_"] = ([_line(-150, B, 150, B)], "линия по базовой линии, ширина 300")
    g["-"] = ([_line(-50, B - XH / 2, 50, B - XH / 2)], "дефис 100 на половине x-height")
    g["="] = ([_line(-130, y, 130, y) for y in (top_a, top_cap, top_x, B, bot_d)],
              "линейка: линии выносной/заглавной/строчной/базовой/нижней, ширина 260")
    g["#"] = ([_rect(-150, top_a, 150, bot_d)] + [_line(-150, y, 150, y) for y in (top_cap, top_x, B)],
              "сетка 300 x (выносной..нижний) с линиями заглавной/строчной/базовой")
    sq = _rect(-60, B - 120, 60, B)
    g["a"] = ([sq, [(-200.0, B)], [(200.0, B)]],
              "квадрат 120 + одиночные move-to (1 точка) на x=±200: учитывает ли их интервал?")
    g["b"] = ([sq], "тот же квадрат 120 без якорей (сравнить с a)")
    g["c"] = ([sq, [(-200.0, B), (-200.0, B)], [(200.0, B), (200.0, B)]],
              "квадрат + штрихи нулевой длины на ±200: видна ли точка пера?")
    g["d"] = ([_rect(0, B - 120, 120, B)], "квадрат СДВИНУТ вправо (x 0..120): центрирует ли приложение?")
    g["e"] = ([_rect(-120, B - 120, 0, B)], "квадрат СДВИНУТ влево (x -120..0)")
    g["f"] = ([_line(x, top_cap, x, B) for x in (-150, -145, -135, -120, -100, -75, -45, -10, 30, 75, 125)],
              "вертикали с зазорами 5,10,15,20,25,30,35,40,45,50: где сливаются — толщина пера")
    g["g"] = ([[(0.0, B - 40), (3.0, B - 43), (6.0, B - 40), (3.0, B - 36), (-2.0, B - 39), (0.0, B - 46)],
               [(60.0, B - 40), (61.0, B - 40)]],
              "спираль-точка (6 точек) и штрих длиной 1 — как выглядят точки")
    g["y"] = ([_line(0, top_x, 0, bot_d)], "вертикаль от строчной до нижнего выносного")
    return g


NEW_CODE_CANDIDATES = [0x0416, 0x044F, 0x00A7, 0x2116, 0x20BD, 0x2603]


def build_calibration(template: str, output: str, tm: TargetMetrics
                      ) -> Tuple[GFont, List[str], List[int]]:
    gf = read_gfont(template)
    lines = []
    written: List[int] = []
    for ch, (strokes, desc) in calibration_glyphs(tm).items():
        gf.set_glyph(ord(ch), strokes)
        written.append(ord(ch))
        lines.append(f"  {ch!r:6} {desc}")
    B, CAP = tm.baseline, tm.cap_height
    new_mark = [_rect(-100, B - CAP, 100, B), _line(-100, B - CAP, 100, B), _line(100, B - CAP, -100, B)]
    added = []
    for code in NEW_CODE_CANDIDATES:
        if code not in gf:
            gf.set_glyph(code, new_mark)
            added.append(code)
            written.append(code)
        if len(added) >= 3:
            break
    if added:
        lines.append("  НОВЫЕ коды (не было в шаблоне), нарисованы как перечёркнутый прямоугольник: "
                     + " ".join(f"{chr(c)} (U+{c:04X})" for c in added))
    else:
        lines.append("  (все кандидаты на новые коды уже есть в шаблоне — тест новых кодов пропущен)")
    gf.save(output)
    return gf, lines, written
