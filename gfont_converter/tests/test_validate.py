import struct

from conftest import make_template_bytes
from gfont.format import encode_glyph, parse_gfont
from gfont.validate import validate_bytes


def test_valid_template_passes():
    rep = validate_bytes(make_template_bytes(), required=[ord("H"), ord("o")])
    assert rep.ok, rep.summary()
    assert rep.prefix_count == 2


def _with(record_code, record):
    gf = parse_gfont(make_template_bytes())
    gf.set_raw(record_code, record)
    return gf


def test_nan_detected():
    gf = _with(ord("H"), encode_glyph(ord("H"), [[(float("nan"), 0), (1, 1)]]))
    rep = validate_bytes(gf.to_bytes())
    assert not rep.ok and any("NaN" in e for e in rep.errors)


def test_out_of_range_error_and_template_warning():
    gf = _with(ord("H"), encode_glyph(ord("H"), [[(5000, 0), (1, 1)]]))
    raw = gf.to_bytes()
    assert not validate_bytes(raw).ok
    rep = validate_bytes(raw, strict_codes={ord("o")})   # H — «нетронутая запись шаблона»
    assert rep.ok and rep.warnings


def test_prefix_mismatch_detected():
    gf = parse_gfont(make_template_bytes())
    gf.entries[0x8B9F].data = encode_glyph(0x8B9F, [[(1, 1), (2, 2)]])
    gf.entries[0x8B9F].compressed = None
    rep = validate_bytes(gf.to_bytes())
    assert any("префикс" in e for e in rep.errors)


def test_name_code_mismatch_detected():
    gf = parse_gfont(make_template_bytes())
    e = gf.entries[ord("H")]
    e.data = encode_glyph(ord("I"), [[(0, 0), (1, 1)]])
    e.compressed = None
    rep = validate_bytes(gf.to_bytes())
    assert any("код в заголовке" in x for x in rep.errors)


def test_required_missing_and_empty():
    gf = _with(ord("o"), encode_glyph(ord("o"), []))
    rep = validate_bytes(gf.to_bytes(), required=[ord("o"), ord("Z")])
    assert any("пустой" in e for e in rep.errors)
    assert any("нет обязательного" in e for e in rep.errors)


def test_garbage_file():
    rep = validate_bytes(b"\x00\x00\x00\x05\x00\x00\x00\x02ab\x00\x00\x00\x00junk")
    assert not rep.ok
