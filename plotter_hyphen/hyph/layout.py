"""Разбиение текста на строки заданной ширины с переносами.

Жадный алгоритм, как у программы плоттера: слово за словом, пока помещается.
Когда очередное слово не помещается:

1. если переносы включены — ищется самое правое допустимое место переноса, при котором
   «часть слова + дефис» ещё помещается в строку (ширина считается по глифам, вместе
   с самим дефисом); остаток слова уходит на следующую строку и обрабатывается так же;
2. иначе слово целиком переходит на новую строку (старое поведение).

Слово, которое не помещается даже в пустую строку и не переносится, остаётся
как есть и отмечается в overflow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List

from .rules import MIN_PART_LETTERS, token_breaks

Measure = Callable[[str], float]
HYPHEN = "-"

_CHUNK_RE = re.compile(r"([^\S\n]*)(\S+)")
_OPENERS = "«„“\"'([{"


@dataclass
class LayoutResult:
    lines: List[str]
    overflow: List[int] = field(default_factory=list)   # номера строк (с 0) шире лимита
    hyphens: int = 0                                     # сколько слов перенесено по частям

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def _letters(s: str) -> int:
    return sum(ch.isalpha() for ch in s)


def _chunks(para: str):
    """Пары (пробелы перед словом, слово). Отдельно стоящие знаки (тире, многоточие и т. п.)
    приклеиваются к предыдущему слову, чтобы строка не начиналась со знака препинания."""
    out = []
    for ws, tok in _CHUNK_RE.findall(para):
        if out and not any(c.isalnum() for c in tok) and tok[0] not in _OPENERS:
            pws, ptok = out[-1]
            out[-1] = (pws, ptok + ws + tok)
        else:
            out.append((ws, tok))
    return out


def _wrap_paragraph(para: str, measure: Measure, max_width: float, hyphenate: bool,
                    res: LayoutResult) -> None:
    cur = ""
    first = True
    for ws, tok in _chunks(para):
        sep = ws if (cur or first) else ""      # отступ абзаца сохраняется, в начале
        first = False                           # перенесённой строки пробелов нет
        breaks = token_breaks(tok) if hyphenate else []
        off = 0
        while True:
            prefix = cur + sep
            rest = tok[off:]
            if measure(prefix + rest) <= max_width:
                cur = prefix + rest
                break
            # Самое правое место переноса, при котором часть с дефисом помещается.
            chosen = None
            for b in reversed(breaks):
                if b.pos <= off:
                    break
                if _letters(tok[off:b.pos]) < MIN_PART_LETTERS:
                    continue
                left = tok[off:b.pos] + (HYPHEN if b.hyphen else "")
                if measure(prefix + left) <= max_width:
                    chosen = (b, left)
                    break
            if chosen is not None:
                b, left = chosen
                res.lines.append(prefix + left)
                res.hyphens += 1 if off == 0 else 0
                cur, sep, off = "", "", b.pos
                continue
            if cur:
                # Не помещается и не переносится — слово целиком на новую строку.
                res.lines.append(cur)
                cur, sep = "", ""
                continue
            cur = prefix + rest                 # шире пустой строки: оставляем как есть
            break
    res.lines.append(cur)


def wrap_text(text: str, measure: Measure, max_width: float,
              hyphenate: bool = True) -> LayoutResult:
    """Разбить текст на строки шириной не больше max_width (в единицах measure).

    Переводы строк исходного текста сохраняются (абзацы, пустые строки).
    """
    res = LayoutResult(lines=[])
    for para in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        _wrap_paragraph(para, measure, max_width, hyphenate, res)
    res.overflow = [i for i, line in enumerate(res.lines) if measure(line) > max_width]
    return res
