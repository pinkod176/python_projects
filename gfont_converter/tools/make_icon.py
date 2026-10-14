"""Рисует значок приложения — голову льва вполоборота (чёрно-белая графика с жирным контуром).

Результат: resources/icon.png (256×256) и resources/icon.ico (16…256).
Рисуется с 2-кратным запасом разрешения и уменьшается — края получаются гладкими.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "resources"
K = 2                      # суперсэмплинг
S = 1000 * K
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)


def P(x, y):
    return (x * K, y * K)


def bezier2(a, c, b, n=14):
    return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1])
            for t in (i / n for i in range(n + 1))]


def catmull(points, closed=True, n=12):
    pts = list(points)
    m = len(pts)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = pts[(i - 1) % m] if closed or i > 0 else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if closed or i + 2 < m else pts[(i + 1) % m]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                             for j in range(2)))
    if not closed:
        out.append(pts[-1])
    return out


def flame_outline(spec, curl=0.22):
    """Силуэт гривы: чередование «впадина, кончик». Бока прядей слегка изогнуты (как пламя)."""
    pts = []
    m = len(spec)
    for i in range(m):
        a = spec[i]
        b = spec[(i + 1) % m]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        dx, dy = b[0] - a[0], b[1] - a[1]
        c = (mx - dy * curl, my + dx * curl)     # изгиб в одну сторону — пряди «закручены»
        pts.extend(bezier2(a, c, b)[:-1])
    return pts


def thick(d, pts, w, fill=BLACK):
    pts = [P(x, y) for x, y in pts]
    d.line(pts, fill=fill, width=int(w * K), joint="curve")
    r = w * K / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def lock_shape(base, tip, width, bend):
    """Прядь гривы: изогнутая «запятая» от основания к острому кончику."""
    bx, by = base
    tx, ty = tip
    dx, dy = tx - bx, ty - by
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L                    # нормаль
    cx, cy = (bx + tx) / 2 + nx * bend * L, (by + ty) / 2 + ny * bend * L
    left, right = [], []
    n = 20
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * bx + 2 * (1 - t) * t * cx + t * t * tx
        y = (1 - t) ** 2 * by + 2 * (1 - t) * t * cy + t * t * ty
        # касательная
        gx = 2 * (1 - t) * (cx - bx) + 2 * t * (tx - cx)
        gy = 2 * (1 - t) * (cy - by) + 2 * t * (ty - cy)
        g = math.hypot(gx, gy) or 1.0
        w = width * (1 - t) ** 0.85 * (0.75 + 0.25 * math.sin(math.pi * min(1, t * 1.6)))
        left.append((x - gy / g * w / 2, y + gx / g * w / 2))
        right.append((x + gy / g * w / 2, y - gx / g * w / 2))
    return left + right[::-1]


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    C = (520, 470)

    # ---------------- грива: два кольца прядей, стекающих вниз ----------------
    locks = []
    for ring, (n, rb, rt, w, off) in enumerate(((20, 0.62, 1.00, 125, 0.0),
                                               (17, 0.45, 0.78, 115, 0.5))):
        for i in range(n):
            th = 2 * math.pi * (i + off) / n - math.pi / 2
            # эллипс гривы: шире внизу (борода), чуть вытянут по вертикали
            rx, ry = 420, 450 + (40 if math.sin(th) > 0.3 else 0)
            ux, uy = math.cos(th), math.sin(th)
            base = (C[0] + rx * rb * ux, C[1] + ry * rb * uy)
            jitter = 0.92 + 0.12 * math.sin(7.3 * i + ring)
            tip_r = rt * jitter
            # пряди «стекают»: направление смешано с вертикалью вниз
            vx, vy = ux, uy + 0.55
            vl = math.hypot(vx, vy) or 1.0
            length = (rx * tip_r - rx * rb) * (1.0 if uy < 0.8 else 1.15)
            tip = (base[0] + vx / vl * length, base[1] + vy / vl * length)
            bend = 0.18 if ux >= 0 else -0.18
            locks.append(lock_shape(base, tip, w * (1.1 if ring else 1.0), bend))
    # белый ореол вокруг всей гривы (виден на тёмной панели задач)
    sil = Image.new("L", (S, S), 0)
    ds = ImageDraw.Draw(sil)
    for lk in locks:
        ds.polygon([P(x, y) for x, y in lk], fill=255)
    ds.ellipse([P(C[0] - 300, C[1] - 330), P(C[0] + 300, C[1] + 330)], fill=255)
    img.paste(Image.new("RGBA", (S, S), WHITE), (0, 0), sil.filter(ImageFilter.MaxFilter(2 * 9 * K + 1)))
    d.ellipse([P(C[0] - 300, C[1] - 330), P(C[0] + 300, C[1] + 330)], fill=BLACK)
    for lk in locks:                            # каждая прядь с белой прорезью по краю
        pts = [P(x, y) for x, y in lk]
        d.polygon(pts, fill=BLACK)
        d.line(pts + pts[:1], fill=WHITE, width=7 * K, joint="curve")
    for lk in locks[::3]:                        # часть прядей поверх — прорези видны не везде
        d.polygon([P(x, y) for x, y in lk], fill=BLACK)

    # ---------------- ухо (слева сверху) ----------------
    ear = catmull([(330, 270), (318, 205), (360, 165), (420, 175), (440, 230), (400, 275)], n=10)
    d.polygon([P(x, y) for x, y in ear], fill=BLACK)
    inner = catmull([(350, 250), (345, 210), (375, 190), (410, 200), (418, 235), (390, 258)], n=10)
    d.polygon([P(x, y) for x, y in inner], fill=WHITE)
    thick(d, catmull([(360, 240), (372, 215), (398, 210)], closed=False), 12)

    # ---------------- морда вполоборота: широкий лоб, скулы, крупная «муфта» ----------------
    face = catmull([
        (455, 255), (545, 232), (635, 248), (705, 300), (738, 380), (740, 455), (752, 520),
        (765, 585), (740, 645), (690, 688), (625, 712), (555, 715), (490, 690), (435, 640),
        (398, 570), (382, 490), (384, 400), (408, 320),
    ], n=10)
    d.polygon([P(x, y) for x, y in face], fill=WHITE)
    d.line([P(x, y) for x, y in face + face[:1]], fill=BLACK, width=24 * K, joint="curve")

    # шерсть: зубцы контура внутрь на левой щеке и подбородке
    for tooth in ([(386, 470), (428, 492), (390, 520)], [(398, 560), (442, 575), (412, 605)],
                  [(430, 630), (478, 642), (458, 675)], [(492, 680), (535, 678), (525, 712)]):
        d.polygon([P(x, y) for x, y in tooth], fill=BLACK)
    # вихор на лбу
    thick(d, catmull([(520, 250), (548, 290), (560, 335)], closed=False), 11)
    thick(d, catmull([(585, 248), (590, 290), (580, 330)], closed=False), 9)

    # ---------------- брови: тяжёлые, «нахмуренные» к переносице ----------------
    brow_l = [(408, 390), (450, 368), (510, 375), (562, 410), (548, 428), (505, 406), (455, 400),
              (415, 408)]
    brow_r = [(598, 412), (638, 374), (690, 366), (730, 384), (722, 402), (688, 392), (645, 402),
              (610, 428)]
    for br in (brow_l, brow_r):
        d.polygon([P(x, y) for x, y in catmull(br, n=6)], fill=BLACK)

    # ---------------- глаза: внутренний уголок ниже — хмурый взгляд ----------------
    for (pts_eye, pupil) in (([(432, 424), (470, 414), (515, 418), (546, 436), (502, 442), (458, 438)],
                              (503, 428)),
                             ([(614, 436), (646, 418), (690, 412), (724, 420), (694, 438), (650, 444)],
                              (668, 428))):
        eye = catmull(pts_eye, n=6)
        d.polygon([P(x, y) for x, y in eye], fill=WHITE)
        d.line([P(x, y) for x, y in eye + eye[:1]], fill=BLACK, width=11 * K, joint="curve")
        px, py = pupil
        d.ellipse([P(px - 11, py - 11), P(px + 11, py + 11)], fill=BLACK)
        d.ellipse([P(px - 1, py - 7), P(px + 5, py - 1)], fill=WHITE)

    # ---------------- переносица и нос ----------------
    thick(d, catmull([(556, 425), (568, 490), (585, 545)], closed=False), 12)
    thick(d, catmull([(612, 425), (640, 490), (672, 540)], closed=False), 11)
    nose = catmull([(570, 548), (625, 528), (690, 536), (712, 566), (672, 604), (630, 614),
                    (590, 600)], n=8)
    d.polygon([P(x, y) for x, y in nose], fill=BLACK)
    d.ellipse([P(600, 548), P(626, 562)], fill=WHITE)            # блик на носу

    # ---------------- «муфта», пасть и подбородок ----------------
    thick(d, catmull([(640, 610), (636, 645), (600, 670)], closed=False), 13)
    thick(d, catmull([(636, 645), (680, 660), (722, 638)], closed=False), 12)
    thick(d, catmull([(520, 655), (560, 675), (600, 670)], closed=False), 12)
    thick(d, catmull([(560, 695), (600, 708), (640, 696)], closed=False), 10)
    for (x, y) in ((535, 615), (558, 600), (562, 628), (700, 598), (722, 612), (705, 625)):
        d.ellipse([P(x - 6, y - 6), P(x + 6, y + 6)], fill=BLACK)
    return img.resize((1000, 1000), Image.LANCZOS)


def main():
    art = draw()
    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    canvas.alpha_composite(art, (12, 12))
    OUT.mkdir(exist_ok=True)
    canvas.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
    canvas.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                          (128, 128), (256, 256)])
    return canvas


if __name__ == "__main__":
    main()
