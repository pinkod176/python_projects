import math
import os
import struct

import pytest

from conftest import make_template_bytes, real_templates
from gfont.format import (GFontError, decode_glyph, encode_glyph, parse_gfont, read_gfont,
                          record_length)


def test_encode_layout():
    rec = encode_glyph(0x0430, [[(1.5, -2.0), (3.0, 4.0)], [(5.0, 6.0)]])
    npts = 3
    assert len(rec) == 10 + 4 * (2 * npts) + npts
    code, nf = struct.unpack_from(">HI", rec, 0)
    assert code == 0x0430 and nf == 6
    assert rec[-3:] == bytes([0, 1, 0])
    assert record_length(rec) == len(rec)


def test_decode_roundtrip():
    strokes = [[(0.25, -81.0), (10.0, 20.5), (30.0, 40.0)], [(1.0, 1.0), (2.0, 2.0)]]
    rec = encode_glyph(1072, strokes)
    code, back = decode_glyph(rec)
    assert code == 1072
    assert back == strokes
    assert encode_glyph(code, back) == rec


def test_decode_rejects_bad_records():
    rec = encode_glyph(65, [[(0, 0), (1, 1)]])
    with pytest.raises(GFontError):
        decode_glyph(rec + b"\x00")                # хвост
    with pytest.raises(GFontError):
        decode_glyph(rec[:-1])                     # обрезано
    bad = bytearray(rec)
    bad[-2] = 1                                    # первый флаг не 0
    with pytest.raises(GFontError):
        decode_glyph(bytes(bad))
    bad = bytearray(rec)
    bad[-1] = 7                                    # флаг не 0/1
    with pytest.raises(GFontError):
        decode_glyph(bytes(bad))


def test_code_range():
    with pytest.raises(GFontError):
        encode_glyph(0x10000, [[(0, 0), (1, 1)]])


def test_synthetic_roundtrip_bytes():
    raw = make_template_bytes()
    gf = parse_gfont(raw)
    assert gf.version == 5 and len(gf.opaque) == 80
    assert gf.prefix_codes == [0x8B9F, 0x5C6D]
    assert gf.to_bytes() == raw


def test_set_glyph_updates_prefix():
    gf = parse_gfont(make_template_bytes())
    gf.set_glyph(0x8B9F, [[(0, 0), (5, 5)]])
    assert gf.prefix[0] == gf.raw(0x8B9F)
    gf2 = parse_gfont(gf.to_bytes())
    assert gf2.prefix[0] == gf2.raw(0x8B9F)


def test_cannot_remove_prefix_code():
    gf = parse_gfont(make_template_bytes())
    with pytest.raises(GFontError):
        gf.remove(0x8B9F)


TEMPLATES = real_templates()


@pytest.mark.skipif(not TEMPLATES, reason="эталонные .gfont не найдены в templates/")
@pytest.mark.parametrize("path", TEMPLATES, ids=[os.path.basename(p) for p in TEMPLATES])
def test_real_template_roundtrip(path):
    raw = open(path, "rb").read()
    gf = parse_gfont(raw)
    assert gf.version == 5
    # префикс разобран без остатка: сразу за ним начинается ZIP
    end = 12 + len(gf.opaque) + sum(len(r) for r in gf.prefix)
    assert raw[end:end + 4] == b"PK\x03\x04"
    # префиксные записи побайтово совпадают с zip-записями
    for r in gf.prefix:
        code = struct.unpack_from(">H", r, 0)[0]
        assert gf.raw(code) == r
    # каждая запись: decode -> encode даёт те же байты, длина по формуле
    for code, e in gf.entries.items():
        c, strokes = decode_glyph(e.data)
        assert c == code and e.name == str(code)
        assert encode_glyph(c, strokes) == e.data
        nf = struct.unpack_from(">I", e.data, 2)[0]
        assert len(e.data) == 10 + 4 * nf + sum(len(s) for s in strokes)
    # перезапись даёт побайтово тот же файл
    assert gf.to_bytes() == raw


@pytest.mark.skipif(not TEMPLATES, reason="эталонные .gfont не найдены в templates/")
def test_real_template_high_codes_are_not_alternates():
    """Коды >= 0x8000 — обычные символы (CJK и т.п.), а не «альтернативы код+32768»."""
    for path in TEMPLATES:
        gf = read_gfont(path)
        high = [c for c in gf.codes() if c >= 0x8000]
        orphans = [c for c in high if (c - 0x8000) not in gf]
        assert len(orphans) > 0.9 * len(high)
        same = [c for c in high if (c - 0x8000) in gf and gf.raw(c)[2:] == gf.raw(c - 0x8000)[2:]]
        assert same == []
