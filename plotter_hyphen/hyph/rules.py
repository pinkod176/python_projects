"""Допустимые места переноса по правилам русского языка.

Слоги даёт pyphen со словарём ru_RU (TeX-паттерны), поверх них — фильтр правил:

* перенос только по границе слогов, в каждой части есть гласная;
* минимум 2 буквы остаются на строке и минимум 2 переходят на новую;
* ь, ъ, й не отрываются от предыдущей буквы (паль-то, подъ-езд, чай-ка);
* не разрывается граница приставки и корня (под-ход, раз-бить, рас-сказ);
* слово с дефисом переносится по дефису, дефис остаётся на верхней строке (кто- / то);
* не переносятся числа, слова с латиницей или цифрами, аббревиатуры из заглавных,
  слова короче 5 букв;
* знаки препинания, стоящие вплотную, едут вместе со своей частью слова:
  открывающие остаются на верхней строке, закрывающие — на нижней.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List

import pyphen

VOWELS = set("аеёиоуыэюя")
NO_LINE_START = set("ьъй")               # не отрываются от предыдущей буквы
CONSONANTS = set("бвгджзклмнпрстфхцчшщ")
MIN_WORD_LETTERS = 5
MIN_PART_LETTERS = 2

# Приставки на согласную: на их границе слог по фонетике часто «переезжает»,
# а переносить так нельзя (не «по-дход», не «подх-од», а «под-ход»).
_PREFIXES = sorted(
    ["без", "бес", "вз", "вс", "воз", "вос", "из", "ис", "низ", "нис", "об", "обез",
     "обес", "от", "под", "пред", "раз", "рас", "роз", "рос", "над", "сверх",
     "через", "черес", "чрез", "меж"],
    key=len, reverse=True)

_CORE_RE = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")


@dataclass(frozen=True)
class Break:
    pos: int       # левая часть — token[:pos]
    hyphen: bool   # True — к левой части дописывается «-»; False — перенос по дефису слова


@lru_cache(maxsize=1)
def _dic() -> pyphen.Pyphen:
    return pyphen.Pyphen(lang="ru_RU", left=MIN_PART_LETTERS, right=MIN_PART_LETTERS)


def _prefix_forbidden(w: str) -> set:
    for p in _PREFIXES:
        if w.startswith(p) and len(w) >= len(p) + 3:
            nxt = w[len(p)]
            n = len(p)
            if nxt in CONSONANTS:
                return {n - 1, n + 1}
            if nxt == "ы":            # ра-зыскать, а не раз-ыскать
                return {n}
            return set()
    return set()


@lru_cache(maxsize=4096)
def word_breaks(word: str) -> tuple:
    """Места переноса внутри одного слова без дефисов (индексы в слове)."""
    if len(word) < MIN_WORD_LETTERS or not word.isalpha():
        return ()
    if not re.fullmatch(r"[А-Яа-яЁё]+", word):
        return ()                      # латиница и прочие алфавиты
    if word.isupper():
        return ()                      # аббревиатура (ООО, МГУ, ...)
    w = word.lower()
    forbidden = _prefix_forbidden(w)
    out = []
    for p in _dic().positions(w):
        if p < MIN_PART_LETTERS or len(w) - p < MIN_PART_LETTERS:
            continue
        if w[p] in NO_LINE_START:
            continue
        if not VOWELS & set(w[:p]) or not VOWELS & set(w[p:]):
            continue
        if p in forbidden:
            continue
        out.append(p)
    return tuple(out)


def split_token(token: str):
    """Токен -> (открывающие знаки, слово, закрывающие знаки)."""
    i = 0
    while i < len(token) and not token[i].isalnum():
        i += 1
    j = len(token)
    while j > i and not token[j - 1].isalnum():
        j -= 1
    return token[:i], token[i:j], token[j:]


def token_breaks(token: str) -> List[Break]:
    """Все допустимые места переноса в токене (слово со знаками препинания вплотную).

    Индексы — в самом токене, по возрастанию.
    """
    lead, core, _trail = split_token(token)
    if not core or not _CORE_RE.fullmatch(core):
        return []
    letters = sum(ch.isalpha() for ch in core)
    if letters < MIN_WORD_LETTERS:
        return []
    if core.replace("-", "").isupper():
        return []
    base = len(lead)
    out: List[Break] = []
    start = 0
    parts = core.split("-")
    for k, part in enumerate(parts):
        if k > 0:
            left = core[:start]
            right = core[start:]
            if (sum(c.isalpha() for c in left) >= MIN_PART_LETTERS
                    and sum(c.isalpha() for c in right) >= MIN_PART_LETTERS):
                out.append(Break(base + start, hyphen=False))
        for p in word_breaks(part):
            out.append(Break(base + start + p, hyphen=True))
        start += len(part) + 1
    return sorted(out, key=lambda b: b.pos)


def show_breaks(token: str, mark: str = "|") -> str:
    """Токен с отметками мест переноса: «про|грам|ми|ро|ва|ние», «кто-|то»."""
    out, prev = [], 0
    for b in token_breaks(token):
        out.append(token[prev:b.pos])
        prev = b.pos
    out.append(token[prev:])
    return mark.join(out)
