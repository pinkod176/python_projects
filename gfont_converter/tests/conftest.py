import glob
import os
import struct
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from gfont.format import GFont, encode_glyph, parse_gfont  # noqa: E402

TEMPLATE_DIR = os.environ.get("GFONT_TEMPLATES", os.path.join(ROOT, "templates"))

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    r"C:\Windows\Fonts\DejaVuSans.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def real_templates():
    return sorted(glob.glob(os.path.join(TEMPLATE_DIR, "*.gfont")))


def make_template_bytes() -> bytes:
    """Синтетический шаблон: структура как у эталонов (префикс + zip)."""
    cjk1 = encode_glyph(0x8B9F, [[(0, -300), (100, -100)], [(0, 0), (50, 50)]])
    cjk2 = encode_glyph(0x5C6D, [[(-50, -200), (50, -200)]])
    gf = GFont(version=5, opaque=bytes(range(80)), prefix=[cjk1, cjk2])
    gf.set_raw(0x8B9F, cjk1)
    gf.set_raw(0x5C6D, cjk2)
    gf.set_glyph(ord("H"), [[(-80, -400), (-80, -85)], [(80, -400), (80, -85)]])
    gf.set_glyph(ord("o"), [[(0, -300), (50, -200), (0, -85), (-50, -200), (0, -300)]])
    gf.set_glyph(0x0438, [[(0, 0), (10, 10)]])          # «и» — будет заменена
    gf.set_glyph(0x00F8, [[(0, 0), (10, 10)]])          # «ø» — будет удалена (нет в charset шрифта?)
    for e in gf.entries.values():
        e.flag_bits = 0x800
    return gf.to_bytes()


@pytest.fixture
def template_path(tmp_path):
    p = tmp_path / "template.gfont"
    p.write_bytes(make_template_bytes())
    return str(p)


@pytest.fixture
def test_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    pytest.skip("не найден тестовый TTF (DejaVu Sans / Arial)")
