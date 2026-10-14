"""Чтение и запись файлов .gfont.

Структура файла (всё, кроме ZIP, — big-endian):

    u32 version (=5)
    u32 L                     длина непрозрачного блока
    L байт                    непрозрачный блок (назначение неизвестно, копируется как есть)
    u32 K                     число записей глифов в префиксе
    K записей глифов          побайтовые копии zip-записей с теми же кодами
    ZIP                       обычный zip (deflate); смещения внутри zip отсчитываются
                              от начала zip, а не от начала файла

Запись глифа (она же содержимое zip-записи с именем str(code)):

    u16 code
    u32 nf                    = 2 * npts
    nf * float32              пары (x, y)
    u32 npts
    npts * u8                 флаги: 0 = начало штриха, 1 = продолжение

ZIP пишется собственным кодом, чтобы нетронутые записи шаблона копировались
вместе с исходным сжатым потоком без изменений (round-trip даёт тот же файл).
"""

from __future__ import annotations

import math
import struct
import time
import zlib
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Point = Tuple[float, float]
Strokes = List[List[Point]]

GFONT_VERSION = 5
MAX_CODE = 0xFFFF

_LOCAL_SIG = b"PK\x03\x04"
_CENTRAL_SIG = b"PK\x01\x02"
_EOCD_SIG = b"PK\x05\x06"


class GFontError(ValueError):
    """Файл не соответствует ожидаемой структуре."""


# --------------------------------------------------------------------------
# Записи глифов
# --------------------------------------------------------------------------

def record_length(data: bytes, offset: int = 0) -> int:
    """Длина записи глифа, начинающейся с offset (10 + 4*nf + npts)."""
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


def encode_glyph(code: int, strokes: Sequence[Sequence[Point]]) -> bytes:
    """Собрать запись глифа. Пустые штрихи пропускаются."""
    if not 0 <= code <= MAX_CODE:
        raise GFontError(f"код {code} вне диапазона u16")
    xs: List[float] = []
    flags = bytearray()
    for stroke in strokes:
        for i, (x, y) in enumerate(stroke):
            xs.append(float(x))
            xs.append(float(y))
            flags.append(0 if i == 0 else 1)
    npts = len(flags)
    out = bytearray(struct.pack(">HI", code, 2 * npts))
    out += struct.pack(">%df" % (2 * npts), *xs)
    out += struct.pack(">I", npts)
    out += flags
    return bytes(out)


def decode_glyph(data: bytes, strict: bool = True) -> Tuple[int, Strokes]:
    """Разобрать запись глифа в (code, strokes).

    strict=True: запись должна занимать весь буфер, nf == 2*npts,
    флаги только 0/1, первый флаг 0.
    """
    n = record_length(data, 0)
    if strict and n != len(data):
        raise GFontError(f"лишние байты после записи: {len(data) - n}")
    code, nf = struct.unpack_from(">HI", data, 0)
    coords = struct.unpack_from(">%df" % nf, data, 6)
    p = 6 + 4 * nf
    (npts,) = struct.unpack_from(">I", data, p)
    flags = data[p + 4:p + 4 + npts]
    if nf != 2 * npts:
        raise GFontError(f"nf={nf} != 2*npts={2 * npts}")
    if strict:
        if any(f not in (0, 1) for f in flags):
            raise GFontError("флаги должны быть 0 или 1")
        if npts and flags[0] != 0:
            raise GFontError("первый флаг должен быть 0")
    strokes: Strokes = []
    for i in range(npts):
        pt = (coords[2 * i], coords[2 * i + 1])
        if flags[i] == 0 or not strokes:
            strokes.append([pt])
        else:
            strokes[-1].append(pt)
    return code, strokes


# --------------------------------------------------------------------------
# ZIP
# --------------------------------------------------------------------------

@dataclass
class ZipEntry:
    """Одна zip-запись. compressed хранится для нетронутых записей шаблона."""
    name: str
    data: bytes
    compressed: Optional[bytes] = None
    crc: Optional[int] = None
    flag_bits: int = 0
    dos_time: int = 0
    dos_date: int = 0
    external_attr: int = 0
    create_version: int = 20
    create_system: int = 0
    extract_version: int = 20

    def ensure_compressed(self, level: int = 6) -> None:
        if self.compressed is None or self.crc is None:
            co = zlib.compressobj(level, zlib.DEFLATED, -15)
            self.compressed = co.compress(self.data) + co.flush()
            self.crc = zlib.crc32(self.data) & 0xFFFFFFFF


def _dos_datetime(t: Optional[float] = None) -> Tuple[int, int]:
    lt = time.localtime(t)
    dos_time = (lt.tm_hour << 11) | (lt.tm_min << 5) | (lt.tm_sec // 2)
    dos_date = ((max(lt.tm_year, 1980) - 1980) << 9) | (lt.tm_mon << 5) | lt.tm_mday
    return dos_time, dos_date


def read_zip(buf: bytes) -> List[ZipEntry]:
    """Разобрать zip, расположенный в buf с позиции 0 (смещения относительные)."""
    eocd = buf.rfind(_EOCD_SIG)
    if eocd < 0:
        raise GFontError("не найден конец ZIP (EOCD)")
    (_, _, _, _, total, cd_size, cd_off, comment_len) = struct.unpack_from(
        "<IHHHHIIH", buf, eocd)
    entries: List[ZipEntry] = []
    p = cd_off
    for _ in range(total):
        if buf[p:p + 4] != _CENTRAL_SIG:
            raise GFontError(f"повреждён central directory по смещению {p}")
        (_, made, need, flags, method, mtime, mdate, crc, csize, usize,
         nlen, xlen, clen, _disk, _iattr, eattr, loff) = struct.unpack_from(
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
        if len(data) != usize or (zlib.crc32(data) & 0xFFFFFFFF) != crc:
            raise GFontError(f"CRC/длина не сходятся у записи {name}")
        entries.append(ZipEntry(
            name=name, data=data, compressed=comp if method == 8 else None,
            crc=crc if method == 8 else None, flag_bits=flags, dos_time=mtime,
            dos_date=mdate, external_attr=eattr, create_version=made & 0xFF,
            create_system=made >> 8, extract_version=need))
    return entries


def build_zip(entries: Iterable[ZipEntry], level: int = 6) -> bytes:
    out = bytearray()
    central = bytearray()
    count = 0
    for e in entries:
        e.ensure_compressed(level)
        name = e.name.encode("utf-8")
        offset = len(out)
        out += struct.pack("<IHHHHHIIIHH", 0x04034B50, e.extract_version, e.flag_bits,
                           8, e.dos_time, e.dos_date, e.crc, len(e.compressed),
                           len(e.data), len(name), 0)
        out += name
        out += e.compressed
        central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50,
                               (e.create_system << 8) | e.create_version,
                               e.extract_version, e.flag_bits, 8, e.dos_time,
                               e.dos_date, e.crc, len(e.compressed), len(e.data),
                               len(name), 0, 0, 0, 0, e.external_attr, offset)
        central += name
        count += 1
    if count > 0xFFFF:
        raise GFontError("слишком много записей для ZIP без Zip64")
    cd_off = len(out)
    out += central
    out += struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, count, count,
                       len(central), cd_off, 0)
    return bytes(out)


# --------------------------------------------------------------------------
# Файл целиком
# --------------------------------------------------------------------------

@dataclass
class GFont:
    version: int
    opaque: bytes
    prefix: List[bytes]                      # K записей префикса (сырые байты)
    entries: Dict[int, ZipEntry] = field(default_factory=dict)  # порядок = порядок в zip

    # ---- доступ ----
    @property
    def prefix_codes(self) -> List[int]:
        return [struct.unpack_from(">H", r, 0)[0] for r in self.prefix]

    def codes(self) -> List[int]:
        return list(self.entries)

    def __contains__(self, code: int) -> bool:
        return code in self.entries

    def raw(self, code: int) -> bytes:
        return self.entries[code].data

    def strokes(self, code: int) -> Strokes:
        return decode_glyph(self.entries[code].data)[1]

    # ---- изменение ----
    def _template_entry(self) -> ZipEntry:
        if self.entries:
            return next(iter(self.entries.values()))
        t, d = _dos_datetime()
        return ZipEntry(name="", data=b"", dos_time=t, dos_date=d)

    def set_raw(self, code: int, record: bytes) -> None:
        """Заменить (на месте) или добавить (в конец) запись глифа."""
        rcode = struct.unpack_from(">H", record, 0)[0]
        if rcode != code:
            raise GFontError(f"код в записи {rcode} != {code}")
        old = self.entries.get(code)
        base = old or self._template_entry()
        self.entries[code] = ZipEntry(
            name=str(code), data=record, flag_bits=base.flag_bits,
            dos_time=base.dos_time, dos_date=base.dos_date,
            external_attr=base.external_attr, create_version=base.create_version,
            create_system=base.create_system, extract_version=base.extract_version)
        # Префиксные записи обязаны совпадать с zip-записями.
        for i, r in enumerate(self.prefix):
            if struct.unpack_from(">H", r, 0)[0] == code:
                self.prefix[i] = record

    def set_glyph(self, code: int, strokes: Sequence[Sequence[Point]]) -> None:
        self.set_raw(code, encode_glyph(code, strokes))

    def remove(self, code: int) -> None:
        if code in self.prefix_codes:
            raise GFontError(f"код {code:#x} используется в префиксе, удалять нельзя")
        self.entries.pop(code, None)

    # ---- сериализация ----
    def to_bytes(self, level: int = 6) -> bytes:
        head = bytearray(struct.pack(">II", self.version, len(self.opaque)))
        head += self.opaque
        head += struct.pack(">I", len(self.prefix))
        for r in self.prefix:
            head += r
        return bytes(head) + build_zip(self.entries.values(), level)

    def save(self, path: str, level: int = 6) -> None:
        data = self.to_bytes(level)
        with open(path, "wb") as f:
            f.write(data)


def parse_gfont(buf: bytes) -> GFont:
    if len(buf) < 12:
        raise GFontError("файл слишком короткий")
    version, L = struct.unpack_from(">II", buf, 0)
    if 8 + L + 4 > len(buf):
        raise GFontError(f"L={L} выходит за пределы файла")
    opaque = bytes(buf[8:8 + L])
    (K,) = struct.unpack_from(">I", buf, 8 + L)
    off = 12 + L
    prefix: List[bytes] = []
    for _ in range(K):
        n = record_length(buf, off)
        prefix.append(bytes(buf[off:off + n]))
        off += n
    if buf[off:off + 4] != _LOCAL_SIG:
        pk = buf.find(_LOCAL_SIG)
        raise GFontError(f"после префикса ожидался ZIP на {off}, первая сигнатура PK на {pk}")
    zentries = read_zip(buf[off:])
    entries: Dict[int, ZipEntry] = {}
    for e in zentries:
        try:
            code = int(e.name)
        except ValueError:
            raise GFontError(f"имя записи не число: {e.name!r}")
        if code in entries:
            raise GFontError(f"дублирующаяся запись {code}")
        entries[code] = e
    return GFont(version=version, opaque=opaque, prefix=prefix, entries=entries)


def read_gfont(path: str) -> GFont:
    with open(path, "rb") as f:
        return parse_gfont(f.read())


def finite(v: float) -> bool:
    return not (math.isnan(v) or math.isinf(v))
