"""Проверка переносов на примерах из задания.

    python check_examples.py                      # условная ширина: каждая буква 100 ед.
    python check_examples.py "Мой почерк.gfont"   # ширины по глифам настоящего шрифта

Для каждого слова печатаются допустимые места переноса и как слово ляжет, если в строке
после «Тест » осталось место примерно на 60 % слова.
"""

import sys

from hyph.gfont import read_gfont
from hyph.layout import wrap_text
from hyph.metrics import Metrics
from hyph.rules import show_breaks

WORDS = ["программирование", "подъезд", "чайка", "классный", "кто-то", "объявление",
         "1234567", "ООО", "автор", "обезьяна"]


def main(argv):
    if len(argv) > 1:
        m = Metrics.from_glyphs(read_gfont(argv[1]))
        measure, src = m.text_width, f"шрифт {argv[1]}"
    else:
        measure, src = (lambda s: 100.0 * len(s)), "условная ширина 100 ед. на символ"
    print(f"Ширины: {src}\n")
    print(f"{'слово':18} {'места переноса':26} строки при нехватке места")
    print("-" * 80)
    for w in WORDS:
        prefix = "Тест "
        limit = measure(prefix) + 0.6 * measure(w) + measure("-")
        on = wrap_text(prefix + w, measure, limit, hyphenate=True).lines
        off = wrap_text(prefix + w, measure, limit, hyphenate=False).lines
        print(f"{w:18} {show_breaks(w):26} {' / '.join(on)}")
        if on != off:
            print(f"{'':18} {'(переносы выключены)':26} {' / '.join(off)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
