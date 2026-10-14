"""Рисует значок приложения — чёрно-белую голову льва: resources/icon.png и resources/icon.ico."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "resources"
S = 1024
C = (512, 520)            # центр головы
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)


def tuft(cx, cy, ang, r0, r1, half_w):
    """Прядь гривы: изогнутый «язычок пламени» от радиуса r0 до острия на r1."""
    pts = []
    n = 24
    curl = 0.35           # пряди слегка закручены, как у нарисованной от руки гривы
    for i in range(n + 1):           # одна сторона
        t = i / n
        r = r0 + (r1 - r0) * t
        w = half_w * math.sin(math.pi * (1 - t) * 0.5 + 0.0) * (1 - t) ** 0.6
        a = ang + curl * t * t - w / max(r, 1)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    for i in range(n, -1, -1):       # другая сторона
        t = i / n
        r = r0 + (r1 - r0) * t
        w = half_w * math.sin(math.pi * (1 - t) * 0.5) * (1 - t) ** 0.6
        a = ang + curl * t * t + w / max(r, 1)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def face_poly(cx, cy, a, b):
    """Морда: широкий лоб и скулы, сужение к подбородку."""
    pts = []
    for i in range(240):
        t = 2 * math.pi * i / 240
        s = math.sin(t)
        x = a * math.cos(t) * (1 - 0.30 * max(0.0, s) ** 1.5)
        y = b * s * (0.92 if s < 0 else 1.0)
        pts.append((cx + x, cy + y))
    return pts


def draw_lion(size=S):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = C

    # --- грива: силуэт из заострённых прядей, всё внутри квадрата
    n = 22
    R_in, R_out = 350, 466
    def mane(grow):
        pts = []
        for i in range(n * 40):
            th = 2 * math.pi * i / (n * 40)
            f = (n * th / (2 * math.pi)) % 1.0
            tip = (1 - abs(2 * f - 1)) ** 2.2      # острые кончики, вогнутые бока
            r = R_in + (R_out - R_in) * tip + grow
            a = th - math.pi / 2 + 0.06 * tip      # лёгкий завиток кончика
            pts.append((cx + r * math.cos(a), cy + 15 + r * 0.98 * math.sin(a)))
        return pts
    # белый контур вокруг гривы (расширенный силуэт): значок виден и на тёмной панели задач
    sil = Image.new("L", (size, size), 0)
    ImageDraw.Draw(sil).polygon(mane(0), fill=255)
    halo = sil.filter(ImageFilter.MaxFilter(25))
    img.paste(Image.new("RGBA", (size, size), WHITE), (0, 0), halo)
    d.polygon(mane(0), fill=BLACK)

    # белые линии вдоль прядей (видны на больших размерах)
    for i in range(n):
        th = 2 * math.pi * i / n - math.pi / 2       # по середине пряди
        line = []
        for k in range(10):
            t = k / 9
            r = 300 + 110 * t
            a = th + 0.05 * t
            line.append((cx + r * math.cos(a), cy + 15 + r * 0.98 * math.sin(a)))
        d.line(line, fill=WHITE, width=12, joint="curve")

    # --- уши
    for sx in (-1, 1):
        ex, ey = cx + sx * 170, cy - 200
        d.ellipse([ex - 58, ey - 58, ex + 58, ey + 58], fill=WHITE)
        d.ellipse([ex - 30, ey - 30, ex + 30, ey + 30], fill=BLACK)

    # --- морда
    d.polygon(face_poly(cx, cy + 20, 245, 255), fill=WHITE)

    # брови и глаза
    for sx in (-1, 1):
        ex, ey = cx + sx * 92, cy - 20
        d.line([(ex - sx * 70, ey - 52), (ex - sx * 5, ey - 70), (ex + sx * 60, ey - 50)],
               fill=BLACK, width=22, joint="curve")
        eye = [(ex - 52, ey + sx * 0), (ex - 20, ey - 26), (ex + 30, ey - 22),
               (ex + 52, ey + 2), (ex + 20, ey + 22), (ex - 25, ey + 18)]
        d.polygon(eye, fill=BLACK)
        d.ellipse([ex - 8 + sx * 6, ey - 12, ex + 8 + sx * 6, ey + 4], fill=WHITE)

    # переносица
    for sx in (-1, 1):
        d.line([(cx + sx * 30, cy - 40), (cx + sx * 40, cy + 70), (cx + sx * 60, cy + 105)],
               fill=BLACK, width=14, joint="curve")

    # нос
    nose = [(cx - 72, cy + 98), (cx + 72, cy + 98), (cx + 52, cy + 140), (cx, cy + 170),
            (cx - 52, cy + 140)]
    d.polygon(nose, fill=BLACK)

    # рот «ω» и подбородок
    d.line([(cx, cy + 168), (cx, cy + 205)], fill=BLACK, width=16)
    for sx in (-1, 1):
        pts = [(cx + sx * t, cy + 205 + 38 * math.sin(math.pi * t / 110)) for t in range(0, 111, 5)]
        d.line(pts, fill=BLACK, width=16, joint="curve")
    d.line([(cx - 45, cy + 262), (cx, cy + 275), (cx + 45, cy + 262)], fill=BLACK, width=12,
           joint="curve")

    # точки усов
    for sx in (-1, 1):
        for (dx, dy) in ((95, 175), (125, 205), (100, 230), (140, 170)):
            x, y = cx + sx * dx, cy + dy
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=BLACK)
    return img


def main() -> None:
    big = draw_lion()
    OUT.mkdir(exist_ok=True)
    big.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
    big.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                       (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
