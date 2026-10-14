"""Самопроверка готового .gfont."""

from __future__ import annotations

import io
import math
import struct
import unicodedata
import zipfile
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Set

from .format import GFontError, decode_glyph, parse_gfont

COORD_LIMIT = 2000.0


@dataclass
class ValidationReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total: int = 0
    low_codes: int = 0          # коды < 0x8000
    high_codes: int = 0         # коды >= 0x8000 (CJK, PUA, полноширинные — НЕ альтернативы)
    prefix_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        lines = [
            f"Записей в ZIP: {self.total} (коды < 0x8000: {self.low_codes}, "
            f">= 0x8000: {self.high_codes}); записей в префиксе: {self.prefix_count}",
        ]
        for w in self.warnings[:30]:
            lines.append("  предупреждение: " + w)
        if len(self.warnings) > 30:
            lines.append(f"  ... и ещё {len(self.warnings) - 30} предупреждений")
        for e in self.errors[:50]:
            lines.append("  ОШИБКА: " + e)
        if len(self.errors) > 50:
            lines.append(f"  ... и ещё {len(self.errors) - 50} ошибок")
        lines.append("Проверка: " + ("OK" if self.ok else "НЕ ПРОЙДЕНА"))
        return "\n".join(lines)


def _label(code: int) -> str:
    ch = chr(code)
    name = unicodedata.name(ch, "")
    return f"U+{code:04X} {ch!r} {name}".strip()


def validate_bytes(buf: bytes, required: Iterable[int] = (),
                   strict_codes: Optional[Set[int]] = None,
                   limit: float = COORD_LIMIT) -> ValidationReport:
    """Проверить файл.

    required     — коды, которые обязаны присутствовать и быть непустыми.
    strict_codes — коды записей, созданных конвертером: для них выход за limit —
                   ошибка; для остальных (нетронутые записи шаблона) — предупреждение.
    """
    rep = ValidationReport()
    try:
        gf = parse_gfont(buf)
    except GFontError as exc:
        rep.errors.append(f"структура файла: {exc}")
        return rep

    if gf.version != 5:
        rep.warnings.append(f"version={gf.version}, в эталонах всегда 5")

    # ZIP открывается стандартным zipfile по всему файлу?
    try:
        zf = zipfile.ZipFile(io.BytesIO(buf))
        bad = zf.testzip()
        if bad is not None:
            rep.errors.append(f"zipfile.testzip: повреждена запись {bad}")
        if len(zf.infolist()) != len(gf.entries):
            rep.errors.append("zipfile видит другое число записей")
    except zipfile.BadZipFile as exc:
        rep.errors.append(f"zipfile не открывает файл: {exc}")

    rep.total = len(gf.entries)
    rep.prefix_count = len(gf.prefix)
    far_template = 0
    for code, entry in gf.entries.items():
        if code < 0x8000:
            rep.low_codes += 1
        else:
            rep.high_codes += 1
        if entry.name != str(code):
            rep.errors.append(f"имя записи {entry.name!r} не каноническое")
        data = entry.data
        try:
            rcode, strokes = decode_glyph(data, strict=True)
        except GFontError as exc:
            rep.errors.append(f"{entry.name}: {exc}")
            continue
        nf = struct.unpack_from(">I", data, 2)[0]
        npts = sum(len(s) for s in strokes)
        if len(data) != 10 + 4 * nf + npts:
            rep.errors.append(f"{entry.name}: длина {len(data)} != 10+4*nf+npts")
        if rcode != code:
            rep.errors.append(f"{entry.name}: код в заголовке {rcode}")
        bad_num = False
        too_far = False
        for s in strokes:
            for x, y in s:
                if not (math.isfinite(x) and math.isfinite(y)):
                    bad_num = True
                elif abs(x) >= limit or abs(y) >= limit:
                    too_far = True
        if bad_num:
            rep.errors.append(f"{_label(code)}: NaN/inf в координатах")
        if too_far:
            if strict_codes is None or code in strict_codes:
                rep.errors.append(f"{_label(code)}: координаты за пределами ±{limit:g}")
            else:
                far_template += 1
    if far_template:
        rep.warnings.append(
            f"{far_template} нетронутых записей шаблона имеют координаты за ±{limit:g} "
            "(так было в шаблоне)")

    for i, rec in enumerate(gf.prefix):
        code = struct.unpack_from(">H", rec, 0)[0]
        e = gf.entries.get(code)
        if e is None:
            rep.errors.append(f"префиксная запись #{i} ({code:#x}) отсутствует в ZIP")
        elif e.data != rec:
            rep.errors.append(f"префиксная запись #{i} ({code:#x}) не совпадает с ZIP")

    for code in required:
        e = gf.entries.get(code)
        if e is None:
            rep.errors.append(f"нет обязательного глифа {_label(code)}")
            continue
        try:
            _, strokes = decode_glyph(e.data)
        except GFontError:
            continue
        if not strokes or sum(len(s) for s in strokes) < 2:
            rep.errors.append(f"пустой глиф {_label(code)}")
    return rep


def validate_file(path: str, **kw) -> ValidationReport:
    with open(path, "rb") as f:
        return validate_bytes(f.read(), **kw)
