"""Рендер превью прямо из штрихов .gfont (не из исходного TTF).

Раскладка строки ПРИБЛИЖЁННАЯ: ширина символа = ширина bbox + gap.
Как интервал считает настоящее приложение — неизвестно (см. README, калибровка).
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from PIL import Image, ImageDraw, ImageFont

from .format import GFont, decode_glyph

DEFAULT_LINES = [
    "Съешь же ещё этих мягких французских булок, да выпей чаю.",
    "ш щ м ц д з Д Ц Щ ё й Ё Й ж Ж ф Ф ы Ы ъ ь э ю я б в",
    "The quick brown fox jumps over the lazy dog. HxoI|",
    "0123456789 № % @ * ( ) [ ] / \\ ' \" « » — – ‑ - • ● ○ ■ √",
    "Привет, мир! Как дела? 10:45; 3,14 = 3? (тест) «кавычки»",
]

_COLORS = [(20, 20, 20), (200, 30, 30), (30, 90, 200), (20, 140, 40),
           (170, 90, 0), (140, 0, 160)]


def _font(size: int):
    for name in ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _glyph(gf: GFont, code: int):
    e = gf.entries.get(code)
    if e is None:
        return None
    try:
        return decode_glyph(e.data)[1]
    except Exception:
        return None


def _bbox(strokes):
    xs = [p[0] for s in strokes for p in s]
    ys = [p[1] for s in strokes for p in s]
    return min(xs), max(xs), min(ys), max(ys)


def render_lines(gf: GFont, lines: Sequence[str], out_path: str, *, scale: float = 0.35,
                 pen: float = 9.0, gap: float = 35.0, space: float = 110.0,
                 baseline: float = -85.0, cap: float = 315.0, xheight: float = 220.0,
                 line_height: float = 620.0, color_strokes: bool = False,
                 title: Optional[str] = None) -> List[str]:
    """Нарисовать строки. Возвращает список отсутствующих в файле символов."""
    missing: List[str] = []
    layouts = []
    max_w = 0.0
    for line in lines:
        x = 60.0
        items = []
        for ch in line:
            if ch == " ":
                x += space
                continue
            strokes = _glyph(gf, ord(ch))
            if not strokes:
                if ch not in missing:
                    missing.append(ch)
                items.append((x, None, 120.0))
                x += 120.0 + gap
                continue
            x0, x1, _, _ = _bbox(strokes)
            w = max(x1 - x0, 1.0)
            items.append((x - x0, strokes, w))
            x += w + gap
        layouts.append(items)
        max_w = max(max_w, x + 60)
    top = 90 if title else 30
    W = int(max_w * scale) + 1
    H = int((len(lines) * line_height + 40) * scale) + top
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    if title:
        d.text((10, 8), title, fill=(60, 60, 60), font=_font(20))
    pw = max(1, int(round(pen * scale)))
    for li, items in enumerate(layouts):
        oy = top + (li * line_height + 470) * scale   # где окажется y=0
        for yy, col in ((baseline, (255, 170, 170)), (baseline - xheight, (200, 220, 255)),
                        (baseline - cap, (220, 220, 220))):
            d.line([(0, oy + yy * scale), (W, oy + yy * scale)], fill=col, width=1)
        for ox, strokes, w in items:
            if strokes is None:
                x0 = ox * scale
                d.rectangle([x0, oy + (baseline - cap) * scale, x0 + w * scale,
                             oy + baseline * scale], outline=(230, 0, 0), width=2)
                continue
            for si, s in enumerate(strokes):
                pts = [((ox + x) * scale, oy + y * scale) for x, y in s]
                col = _COLORS[si % len(_COLORS)] if color_strokes else (15, 15, 15)
                if len(pts) == 1:
                    continue  # одиночный move-to (якорь) не рисуем
                d.line(pts, fill=col, width=pw, joint="curve")
                r = pw / 2
                for px, py in (pts[0], pts[-1]):
                    d.ellipse([px - r, py - r, px + r, py + r], fill=col)
    img.save(out_path)
    return missing


def render_sheet(gf: GFont, codes: Sequence[int], out_path: str, *, cols: int = 16,
                 cell: int = 110, baseline: float = -85.0, cap: float = 315.0,
                 xheight: float = 220.0) -> None:
    """Лист глифов: цветные штрихи, зелёная точка — начало штриха, подпись — код."""
    rows = (len(codes) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell, rows * cell), "white")
    d = ImageDraw.Draw(img)
    f = _font(10)
    s = cell / 620.0
    for i, code in enumerate(codes):
        cx = (i % cols) * cell + cell / 2
        top = (i // cols) * cell
        oy = top + 470 * s
        d.rectangle([(i % cols) * cell, top, (i % cols + 1) * cell - 1, top + cell - 1],
                    outline=(225, 225, 225))
        d.line([((i % cols) * cell, oy + baseline * s), ((i % cols + 1) * cell, oy + baseline * s)],
               fill=(255, 190, 190))
        d.line([((i % cols) * cell, oy + (baseline - xheight) * s),
                ((i % cols + 1) * cell, oy + (baseline - xheight) * s)], fill=(215, 230, 255))
        d.text(((i % cols) * cell + 2, top + 1), f"{chr(code)} {code:04X}", fill=(90, 90, 200), font=f)
        strokes = _glyph(gf, code)
        if not strokes:
            d.text((cx - 10, top + cell / 2), "нет", fill=(220, 0, 0), font=f)
            continue
        for si, st in enumerate(strokes):
            pts = [(cx + x * s, oy + y * s) for x, y in st]
            col = _COLORS[si % len(_COLORS)]
            if len(pts) > 1:
                d.line(pts, fill=col, width=2)
            for px, py in pts:
                d.point((px, py), fill=(0, 0, 0))
            px, py = pts[0]
            d.ellipse([px - 2.5, py - 2.5, px + 2.5, py + 2.5], fill=(0, 170, 0))
    img.save(out_path)
