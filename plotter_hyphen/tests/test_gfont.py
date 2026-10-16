import pytest

from hyph.gfont import GFontError, build_gfont, parse_gfont
from hyph.layout import wrap_text
from hyph.metrics import Metrics


def box(w, h=300):
    """Глиф-прямоугольник шириной w, центрированный по X, как в настоящих шрифтах."""
    return [[(-w / 2, -h), (w / 2, -h), (w / 2, 0), (-w / 2, 0)]]


def font(widths):
    return {ord(ch): box(w) for ch, w in widths.items()}


def test_roundtrip():
    glyphs = font({"а": 100, "-": 60})
    back = parse_gfont(build_gfont(glyphs))
    assert set(back) == {ord("а"), ord("-")}
    assert back[ord("а")][0][0] == (-50.0, -300.0)


def test_bad_file():
    with pytest.raises(GFontError):
        parse_gfont(b"not a gfont at all")


def test_text_width_model():
    m = Metrics.from_glyphs(font({"а": 100, "б": 80}), gap=10, space=50)
    assert m.text_width("а") == 100
    assert m.text_width("аб") == 100 + 10 + 80
    assert m.text_width("а б") == 100 + 50 + 80
    assert m.text_width("") == 0


def test_missing_glyph_uses_fallback():
    m = Metrics.from_glyphs(font({"а": 100, "б": 120, "в": 140}), gap=0)
    assert m.text_width("Ж") == 120          # медиана строчных
    assert m.missing_in(["аЖ"]) == ["Ж"]


def test_layout_uses_real_glyph_widths_and_dash():
    letters = {ch: 100 for ch in "абвгдежзийклмнопрстуфхцчшщъыьэюя"}
    letters["ш"] = 300                                   # широкая буква
    narrow = Metrics.from_glyphs(font({**letters, "-": 20}), gap=0, space=100)
    wide = Metrics.from_glyphs(font({**letters, "-": 400}), gap=0, space=100)
    text = "машина машина"
    # "машина " = 100+100+300+100+100+100 + 100 = 900; "ма-" = 200 + дефис
    assert wrap_text(text, narrow.text_width, 1150).lines == ["машина ма-", "шина"]
    # Широкий дефис уже не помещается после "ма" — слово целиком на новую строку.
    assert wrap_text(text, wide.text_width, 1150).lines == ["машина", "машина"]
