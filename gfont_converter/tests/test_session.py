"""Фасад движка для GUI (без Qt)."""

from pathlib import Path

from gfont.charset import parse_charset
from gfont.format import read_gfont
from gfont.session import (CHARSET_PRESETS, FontSession, UiParams, default_template_path,
                           diagnose, variant_paths)
from gfont.normalize import TargetMetrics


def test_presets_parse():
    for key, (title, spec) in CHARSET_PRESETS.items():
        p = UiParams(charset_preset=key, custom_chars="Ж№")
        codes = parse_charset(p.charset_spec())
        assert codes, key
    assert parse_charset(UiParams(charset_preset="custom", custom_chars="аб").charset_spec()) == [0x430, 0x431]
    ru = parse_charset(UiParams(charset_preset="ru").charset_spec())
    assert ord("ё") in ru and ord("A") not in ru
    en = parse_charset(UiParams(charset_preset="en").charset_spec())
    assert len(en) == 52


def test_params_roundtrip():
    p = UiParams(mode="outline", slant=7, liveliness=0.4, seed=9)
    q = UiParams.from_dict(p.to_dict() | {"unknown": 1, "seed": "bad"})
    assert q.mode == "outline" and q.slant == 7 and q.liveliness == 0.4
    assert q.seed == 1                     # некорректное значение -> по умолчанию
    assert abs(UiParams(density=2.0).metrics().step - 12.5) < 1e-9


def test_variant_paths():
    ps = variant_paths(Path("x"), 'Шрифт: "тест"', 3)
    assert [p.name for p in ps] == ["Шрифт_ _тест__1.gfont", "Шрифт_ _тест__2.gfont",
                                    "Шрифт_ _тест__3.gfont"]


def test_diagnose():
    tm = TargetMetrics()
    assert diagnose([], tm) == ["пустой глиф"]
    assert diagnose([[(0, -85), (0, -400)]], tm) == []
    assert any("много штрихов" in w for w in diagnose([[(0, -100), (1, -100)]] * 9, tm))
    assert any("метрики" in w for w in diagnose([[(0, -85), (0, 900)]], tm))


def test_default_template_bundled():
    p = default_template_path()
    assert p.exists(), "resources/с_клода.gfont должен лежать в проекте"
    assert len(read_gfont(p).entries) > 1000


def test_session_glyph_and_convert(tmp_path, test_font, template_path):
    s = FontSession(test_font)
    assert s.glyph_count > 50 and s.family
    p = UiParams(charset_preset="custom", custom_chars="Hoщ.")
    r = s.glyph(ord("щ"), p)
    assert r.strokes and not r.warnings
    # быстрые параметры не требуют повторного извлечения
    n = len(s.cache)
    s.glyph(ord("щ"), UiParams(slant=12))
    assert len(s.cache) == n
    out = tmp_path / "папка с пробелом" / "шрифт 字_1.gfont"
    rep = s.convert(p, out, template_path, log=lambda *a: None, jobs=1)
    assert rep.validation.ok and out.exists()
    # то, что показал предпросмотр, побайтово совпадает с записанным в файл
    gf = read_gfont(out)
    assert gf.strokes(ord("щ")) == s.glyph(ord("щ"), p).strokes
