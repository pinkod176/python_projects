"""Рисует значок приложения: resources/icon.png и resources/icon.ico."""

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "resources"
S = 1024


def main() -> None:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 40, S - 40, S - 40], radius=200, fill=(32, 64, 140, 255))
    d.rounded_rectangle([110, 110, S - 110, S - 110], radius=150, fill=(250, 248, 240, 255))
    # линии тетради
    for y in (430, 640):
        d.line([(150, y), (S - 150, y)], fill=(170, 195, 235, 255), width=10)
    d.line([(150, 760), (S - 150, 760)], fill=(235, 150, 150, 255), width=10)
    # рукописный штрих: курсивная петля «ℓ» с хвостом
    pts = []
    n = 600
    for i in range(n):
        t = i / (n - 1)
        th = 2 * math.pi * t
        x = 250 + 520 * t + 170 * math.sin(th)
        y = 760 - 300 * math.sin(th / 2) ** 2 * (1.6 - t)
        pts.append((x, y))
    w = 22
    for x, y in pts:
        d.ellipse([x - w, y - w, x + w, y + w], fill=(25, 25, 35, 255))
    # точки штриха (как в .gfont)
    for x, y in pts[::50] + [pts[-1]]:
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(225, 60, 60, 255))
    OUT.mkdir(exist_ok=True)
    big = img.resize((256, 256), Image.LANCZOS)
    big.save(OUT / "icon.png")
    img.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                       (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
