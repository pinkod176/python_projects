"""Группы символов для рисования и сведения о форме букв (для выравнивания)."""

from __future__ import annotations

import unicodedata
from typing import Dict, List, Tuple

RU_LOWER = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
RU_UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
EN_LOWER = "abcdefghijklmnopqrstuvwxyz"
EN_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
PUNCT = ".,:;!?…-()[]{}/\\'\"_"
SPECIAL = ("№%@*&#$€₽+−=<>^~|«»„“”‘’—–‑•●○■□√°§©±×÷∞≈≠≤≥←→↑↓")

GROUPS: List[Tuple[str, str]] = [
    ("Строчные русские", RU_LOWER),
    ("Заглавные русские", RU_UPPER),
    ("Строчные английские", EN_LOWER),
    ("Заглавные английские", EN_UPPER),
    ("Цифры", DIGITS),
    ("Знаки препинания", PUNCT),
    ("Спецсимволы", SPECIAL),
]

ALL_CODES: List[int] = [ord(c) for _, chars in GROUPS for c in chars]
GROUP_OF: Dict[int, int] = {ord(c): i for i, (_, chars) in enumerate(GROUPS) for c in chars}

# Нижние выносные элементы: им автовыравнивание по базовой линии не нужно
DESCENDERS = set("дзруфцщgjpqyДЦЩQ,;()[]{}|/\\_„‚")
# Строчные, у которых верх — линия высоты строчных (по ним считается «x-height» почерка)
XHEIGHT_LETTERS = set("авгджзиклмнопрстуцчшщъыьэюяacegmnopqrsuvwxyz")
# Заглавные без надстрочных знаков (по ним считается высота заглавных)
CAP_LETTERS = set(RU_UPPER + EN_UPPER) - set("ЁЙ")
# Знаки, которые стоят на базовой линии (их можно подтягивать к ней)
ON_BASELINE = set(".!?:…%#&$€₽№@") | set(DIGITS)


def char_name(code: int) -> str:
    ch = chr(code)
    return unicodedata.name(ch, f"U+{code:04X}").lower()


def label(code: int) -> str:
    """Подпись символа для списка и подсказок («‑» и похожие невидимые — с названием)."""
    ch = chr(code)
    special = {0x2011: "‑ (неразрывный дефис)", 0x2013: "– (короткое тире)",
               0x2014: "— (длинное тире)", 0x2212: "− (минус)", 0x2D: "- (дефис)",
               0x5F: "_ (подчёркивание)"}
    return special.get(code, ch)


def can_align(code: int) -> bool:
    """Символ стоит на базовой линии без нижних выносных (для автовыравнивания)."""
    ch = chr(code)
    if ch in DESCENDERS:
        return False
    return ch.isalpha() or ch in ON_BASELINE
