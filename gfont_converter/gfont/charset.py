"""Наборы символов и разбор опции --charset."""

from __future__ import annotations

import unicodedata
from typing import Dict, Iterable, List, Set

SOFT_HYPHEN = 0x00AD

PUNCT_SYMBOLS = [
    0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015,          # дефисы и тире (‑ = U+2011)
    0x2018, 0x2019, 0x201A, 0x201C, 0x201D, 0x201E,          # кавычки ‘ ’ ‚ “ ” „
    0x2020, 0x2021, 0x2022, 0x2026, 0x2030, 0x2032, 0x2033,  # † ‡ • … ‰ ′ ″
    0x2039, 0x203A, 0x20AC, 0x20BD, 0x2116, 0x2122,          # ‹ › € ₽ № ™
    0x2190, 0x2191, 0x2192, 0x2193,                          # стрелки
    0x2212, 0x221A, 0x221E, 0x2248, 0x2260, 0x2264, 0x2265,  # − √ ∞ ≈ ≠ ≤ ≥
    0x25A0, 0x25A1, 0x25CB, 0x25CF,                          # ■ □ ○ ●
]

NAMED: Dict[str, List[int]] = {
    "ascii": list(range(0x21, 0x7F)),
    "latin1": [c for c in range(0xA1, 0x100) if c != SOFT_HYPHEN],
    "cyrillic": list(range(0x400, 0x500)),
    "russian": list(range(0x410, 0x450)) + [0x401, 0x451],
    "digits": list(range(0x30, 0x3A)),
    "punct": PUNCT_SYMBOLS,
}
NAMED["default"] = NAMED["ascii"] + NAMED["latin1"] + NAMED["cyrillic"] + NAMED["punct"]

# Если в шрифте нет символа — чем его заменить (по порядку).
FALLBACKS: Dict[int, List[int]] = {
    0x2011: [0x2010, 0x002D],   # неразрывный дефис -> дефис
    0x2010: [0x002D],
    0x2012: [0x2013],
    0x2015: [0x2014],
}


def drawable(code: int) -> bool:
    """Может ли у символа быть рисунок: не пробел, не управляющий, не комбинируемый."""
    if code > 0xFFFF or code == SOFT_HYPHEN:
        return False
    cat = unicodedata.category(chr(code))
    return not (cat.startswith("Z") or cat.startswith("C") or cat.startswith("M"))


def _parse_code(tok: str) -> int:
    t = tok.strip()
    if t.upper().startswith("U+"):
        t = t[2:]
    elif t.lower().startswith("0x"):
        t = t[2:]
    return int(t, 16)


def parse_charset(spec: str) -> List[int]:
    """Разобрать спецификацию набора символов.

    Элементы через запятую:
        default | ascii | latin1 | cyrillic | russian | digits | punct
        U+0410            один код
        U+0400-U+04FF     диапазон (U+ можно опускать: 0400-04FF)
        chars:абв№        перечисление символов (до конца строки, запятые тоже)
        @файл.txt         все символы из текстового файла (UTF-8)
        -элемент          исключить (например -U+0482-U+0489)
    """
    include: Set[int] = set()
    exclude: Set[int] = set()
    rest = spec
    chars_part = ""
    if "chars:" in rest:
        rest, chars_part = rest.split("chars:", 1)
    for raw in rest.split(","):
        tok = raw.strip()
        if not tok:
            continue
        target = include
        if tok.startswith("-") and len(tok) > 1:
            target = exclude
            tok = tok[1:].strip()
        target.update(_expand(tok))
    include.update(ord(c) for c in chars_part)
    codes = sorted(c for c in include - exclude if drawable(c))
    return codes


def _expand(tok: str) -> Iterable[int]:
    low = tok.lower()
    if low in NAMED:
        return NAMED[low]
    if tok.startswith("@"):
        with open(tok[1:], "r", encoding="utf-8-sig") as f:
            return [ord(c) for c in f.read()]
    if "-" in tok[1:]:
        i = tok.index("-", 1)
        a, b = _parse_code(tok[:i]), _parse_code(tok[i + 1:])
        return range(min(a, b), max(a, b) + 1)
    if tok.upper().startswith("U+") or tok.lower().startswith("0x"):
        return [_parse_code(tok)]
    if len(tok) == 1:
        return [ord(tok)]
    raise ValueError(f"не понимаю элемент набора символов: {tok!r}")


def is_core(code: int) -> bool:
    """Основные символы, для которых пустой глиф — ошибка."""
    ch = chr(code)
    cat = unicodedata.category(ch)
    return cat[0] in ("L", "N", "P")
