import os

import numpy as np
import pytest

from gfont.build import ConvertOptions, convert
from gfont.calibrate import build_calibration
from gfont.charset import parse_charset
from gfont.format import read_gfont
from gfont.normalize import TargetMetrics, refine_stroke, spiral
from gfont.preview import render_lines


def test_charset_parsing():
    cs = parse_charset("ascii")
    assert ord("A") in cs and 0x20 not in cs and 0x7F not in cs
    d = parse_charset("default")
    assert 0x00AD not in d                     # мягкий перенос без глифа
    assert all(c <= 0xFFFF for c in d)
    assert ord("№") in d and 0x2011 in d and ord("ё") in d
    assert 0x0483 not in d                     # комбинируемые знаки исключены
    assert parse_charset("U+0410-U+0412,chars:№") == [0x410, 0x411, 0x412, 0x2116]
    assert ord("Ж") not in parse_charset("russian,-U+0416")


def test_spiral_and_refine():
    tm = TargetMetrics()
    s = spiral(0, -100, 4, tm)
    assert 4 <= len(s) <= 8
    line = np.stack([np.linspace(0, 300, 300), np.zeros(300)], axis=1)
    r = refine_stroke(line, False, tm)
    steps = np.linalg.norm(np.diff(r, axis=0), axis=1)
    assert abs(steps.mean() - tm.step) < 3
    assert np.allclose(r[0], [0, 0]) and np.allclose(r[-1], [300, 0])


CHARS = "Hxo.%(щДЦ@№‑i"


def test_convert_end_to_end(tmp_path, template_path, test_font):
    out = str(tmp_path / "out.gfont")
    opts = ConvertOptions(font=test_font, output=out, template=template_path,
                          charset="chars:" + CHARS + "ø", jobs=1)
    rep = convert(opts, log=lambda *a: None)
    assert rep.validation.ok, rep.text()
    gf = read_gfont(out)
    tm = TargetMetrics()
    assert ord("H") in rep.replaced and ord("o") in rep.replaced
    assert ord("щ") in rep.new
    # префикс шаблона сохранён и согласован
    assert gf.prefix_codes == [0x8B9F, 0x5C6D]
    for code in map(ord, CHARS):
        if code in rep.missing_in_font:
            continue
        strokes = gf.strokes(code)
        assert strokes, chr(code)
        allp = np.array([p for s in strokes for p in s])
        assert np.isfinite(allp).all()
        assert abs(allp[:, 0].min() + allp[:, 0].max()) < 1.0      # центр bbox по X = 0
    # «o» — один замкнутый штрих
    o = gf.strokes(ord("o"))
    assert len(o) == 1 and np.allclose(o[0][0], o[0][-1])
    # «x» — два штриха (сквозное пересечение)
    assert len(gf.strokes(ord("x"))) == 2
    # «H» стоит на базовой линии, высота около высоты заглавной
    h = np.array([p for s in gf.strokes(ord("H")) for p in s])
    assert abs(h[:, 1].max() - tm.baseline) < 15
    assert abs((h[:, 1].max() - h[:, 1].min()) - tm.cap_height) < 25
    # хвост «щ» уходит ниже базовой линии
    sh = np.array([p for s in gf.strokes(ord("щ")) for p in s])
    assert sh[:, 1].max() > tm.baseline + 20
    # «.» — маленькая спираль, не одна точка
    dot = gf.strokes(ord("."))
    assert len(dot) == 1 and len(dot[0]) >= 4
    # U+2011 есть (из шрифта или подстановкой)
    assert 0x2011 in gf


def test_no_new_entries(tmp_path, template_path, test_font):
    out = str(tmp_path / "out.gfont")
    rep = convert(ConvertOptions(font=test_font, output=out, template=template_path,
                                 charset="chars:Hoщ", no_new_entries=True, jobs=1),
                  log=lambda *a: None)
    assert rep.new == [] and rep.skipped_new == [ord("щ")]
    assert ord("щ") not in read_gfont(out)


def test_preview_from_written_file(tmp_path, template_path, test_font):
    out = str(tmp_path / "out.gfont")
    convert(ConvertOptions(font=test_font, output=out, template=template_path,
                           charset="chars:Hxo", jobs=1), log=lambda *a: None)
    png = str(tmp_path / "p.png")
    missing = render_lines(read_gfont(out), ["Hxo Z"], png)
    assert os.path.getsize(png) > 0 and missing == ["Z"]


def test_calibration(tmp_path, template_path):
    out = str(tmp_path / "cal.gfont")
    gf, lines, written = build_calibration(template_path, out, TargetMetrics())
    gf2 = read_gfont(out)
    assert ord("H") in gf2 and ord("9") in gf2 and ord("#") in gf2
    assert len(gf2.strokes(ord("a"))) == 3          # квадрат + 2 одиночных move-to
    assert any(c not in (ord(ch) for ch in "Hoи") for c in written)
