"""Чтение штрихов из файлов .gfont (только чтение).

Формат тот же, что разбирает gfont_converter (gfont/format.py):

    u32 version, u32 L, L байт непрозрачного блока,
    u32 K, K записей глифов (копии zip-записей),
    ZIP, в котором запись с именем str(code) содержит запись глифа:
        u16 code, u32 nf = 2*npts, nf*float32 (x, y), u32 npts, npts*u8 флагов
        (0 — начало штриха, 1 — продолжение).

Всё, кроме ZIP, — big-endian. Ширины символов (advance) в формате нет:
программа плоттера ставит буквы по крайним точкам штрихов (bbox).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Dict, List, Tuple

Point = Tuple[float, float]
Strokes = List[List[Point]]

_LOCAL_SIG = b"PK\x03\x04"
_CENTRAL_SIG = b"PK\x01\x02"
_EOCD_SIG = b"PK\x05\x06"


class GFontError(ValueError):
    """Файл не похож на .gfont или повреждён."""


def _record_length(data: bytes, offset: int) -> int:
    if offset + 6 > len(data):
        raise GFontError("запись глифа обрезана (нет заголовка)")
    (nf,) = struct.unpack_from(">I", data, offset + 2)
    p = offset + 6 + 4 * nf
    if p + 4 > len(data):
        raise GFontError("запись глифа обрезана (координаты)")
    (npts,) = struct.unpack_from(">I", data, p)
    end = p + 4 + npts
    if end > len(data):
        raise GFontError("запись глифа обрезана (флаги)")
    return end - offset


def decode_glyph(data: bytes) -> Tuple[int, Strokes]:
    """Запись глифа -> (code, штрихи)."""
    _record_length(data, 0)
    code, nf = struct.unpack_from(">HI", data, 0)
    coords = struct.unpack_from(">%df" % nf, data, 6)
    p = 6 + 4 * nf
    (npts,) = struct.unpack_from(">I", data, p)
    flags = data[p + 4:p + 4 + npts]
    if nf != 2 * npts:
        raise GFontError(f"nf={nf} != 2*npts={2 * npts}")
    strokes: Strokes = []
    for i in range(npts):
        pt = (coords[2 * i], coords[2 * i + 1])
        if flags[i] == 0 or not strokes:
            strokes.append([pt])
        else:
            strokes[-1].append(pt)
    return code, strokes


def _read_zip(buf: bytes) -> Dict[str, bytes]:
    eocd = buf.rfind(_EOCD_SIG)
    if eocd < 0:
        raise GFontError("не найден конец ZIP (EOCD)")
    (_, _, _, _, total, _cd_size, cd_off, _clen) = struct.unpack_from("<IHHHHIIH", buf, eocd)
    out: Dict[str, bytes] = {}
    p = cd_off
    for _ in range(total):
        if buf[p:p + 4] != _CENTRAL_SIG:
            raise GFontError(f"повреждён central directory по смещению {p}")
        (_, _made, _need, flags, method, _mt, _md, _crc, csize, usize,
         nlen, xlen, clen, _disk, _ia, _ea, loff) = struct.unpack_from(
            "<IHHHHHHIIIHHHHHII", buf, p)
        name = buf[p + 46:p + 46 + nlen].decode("utf-8" if flags & 0x800 else "cp437")
        p += 46 + nlen + xlen + clen
        if buf[loff:loff + 4] != _LOCAL_SIG:
            raise GFontError(f"нет локального заголовка для {name}")
        lnlen, lxlen = struct.unpack_from("<HH", buf, loff + 26)
        start = loff + 30 + lnlen + lxlen
        comp = bytes(buf[start:start + csize])
        if method == 8:
            data = zlib.decompress(comp, -15)
        elif method == 0:
            data = comp
        else:
            raise GFontError(f"неподдерживаемый метод сжатия {method} у {name}")
        if len(data) != usize:
            raise GFontError(f"длина не сходится у записи {name}")
        out[name] = data
    return out


def parse_gfont(buf: bytes) -> Dict[int, Strokes]:
    """Содержимое .gfont -> {код символа: штрихи}. Пустые и битые глифы пропускаются."""
    if len(buf) < 12:
        raise GFontError("файл слишком короткий")
    _version, L = struct.unpack_from(">II", buf, 0)
    if 8 + L + 4 > len(buf):
        raise GFontError(f"L={L} выходит за пределы файла")
    (K,) = struct.unpack_from(">I", buf, 8 + L)
    off = 12 + L
    for _ in range(K):
        off += _record_length(buf, off)
    if buf[off:off + 4] != _LOCAL_SIG:
        raise GFontError(f"после префикса ожидался ZIP на смещении {off}")
    glyphs: Dict[int, Strokes] = {}
    for name, data in _read_zip(buf[off:]).items():
        try:
            code = int(name)
            _, strokes = decode_glyph(data)
        except (ValueError, struct.error):
            continue
        if any(len(s) for s in strokes):
            glyphs[code] = strokes
    return glyphs


def read_gfont(path) -> Dict[int, Strokes]:
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise GFontError(f"не удалось прочитать «{p}»: {exc.strerror or exc}") from exc
    try:
        return parse_gfont(data)
    except (struct.error, zlib.error) as exc:
        raise GFontError(f"файл «{p}» не похож на .gfont или повреждён: {exc}") from exc


def encode_glyph(code: int, strokes) -> bytes:
    """Собрать запись глифа (нужно тестам, чтобы делать маленькие .gfont)."""
    xs: List[float] = []
    flags = bytearray()
    for stroke in strokes:
        for i, (x, y) in enumerate(stroke):
            xs += [float(x), float(y)]
            flags.append(0 if i == 0 else 1)
    out = bytearray(struct.pack(">HI", code, len(xs)))
    out += struct.pack(">%df" % len(xs), *xs)
    out += struct.pack(">I", len(flags)) + flags
    return bytes(out)


def build_gfont(glyphs: Dict[int, Strokes]) -> bytes:
    """Минимальный .gfont из словаря глифов (для тестов; ZIP без сжатия)."""
    head = struct.pack(">II", 5, 0) + struct.pack(">I", 0)
    local = bytearray()
    central = bytearray()
    for code, strokes in glyphs.items():
        rec = encode_glyph(code, strokes)
        name = str(code).encode()
        crc = zlib.crc32(rec) & 0xFFFFFFFF
        off = len(local)
        local += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, 0, 0, 0,
                             crc, len(rec), len(rec), len(name), 0) + name + rec
        central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, 0, 0, 0,
                               crc, len(rec), len(rec), len(name), 0, 0, 0, 0, 0, off) + name
    eocd = struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(glyphs), len(glyphs),
                       len(central), len(local), 0)
    return head + bytes(local) + bytes(central) + eocd
