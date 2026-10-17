"""Самопроверка, которая работает и в собранном exe (у exe нет консоли — пишем в файл).

    PlotterHyphen.exe --selftest  папка [шрифт.gfont]   -> папка\\selftest.txt
    PlotterHyphen.exe --smoke-gui папка                 -> папка\\smoke.txt + window.png
"""

from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path

from .gfont import build_gfont, read_gfont
from .layout import wrap_text
from .metrics import Metrics
from .rules import show_breaks

# Примеры из задания: слово -> допустимые места переноса ("|").
EXAMPLES = {
    "программирование": "про|грам|ми|ро|ва|ние",
    "подъезд": "подъ|езд",
    "чайка": "чай|ка",
    "классный": "класс|ный",
    "кто-то": "кто-|то",
    "объявление": "объ|яв|ле|ние",
    "1234567": "1234567",
    "ООО": "ООО",
    "автор": "ав|тор",
    "обезьяна": "обе|зья|на",
}

SAMPLE = ("Программирование плоттера — интересное занятие. Подъезд, чайка, классный "
          "кто-то, объявление, 1234567, ООО, автор, обезьяна.")

_LETTERS = ("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
            "0123456789.,:;!?()«»—-")


def synthetic_font() -> dict:
    """Шрифт-заглушка: каждый символ — штрих шириной 100 ед., дефис — 60."""
    glyphs = {ord(ch): [[(-50, -300), (50, -300), (50, 0)]] for ch in _LETTERS}
    glyphs[ord("-")] = [[(-30, -150), (30, -150)]]
    return glyphs


def run_selftest(out_dir: str, font_path: str = "") -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines, ok = [], True
    try:
        import pyphen
        lines.append(f"pyphen {getattr(pyphen, '__version__', '?')}, ru_RU: "
                     f"{'ru_RU' in pyphen.LANGUAGES}")
        for word, expected in EXAMPLES.items():
            got = show_breaks(word)
            good = got == expected
            ok &= good
            lines.append(f"{'OK ' if good else 'ОШИБКА'} {word:18} {got}"
                         + ("" if good else f"   (ожидалось {expected})"))
        if font_path:
            glyphs = read_gfont(font_path)
            src = font_path
        else:
            glyphs = synthetic_font()
            src = "встроенная заглушка"
        m = Metrics.from_glyphs(glyphs)
        limit = m.text_width("Программирование плоттера")
        res = wrap_text(SAMPLE, m.text_width, limit)
        lines.append(f"\nРаскладка ({src}, {len(glyphs)} символов), ширина {limit:.0f} ед.:")
        lines += ["    " + ln for ln in res.lines]
        too_wide = [ln for ln in res.lines if m.text_width(ln) > limit]
        bad_start = [ln for ln in res.lines[1:] if ln and not (ln[0].isalnum() or ln[0] in "«(")]
        ok &= not too_wide and not bad_start
        if not font_path:
            ok &= res.hyphens > 0           # на заглушке переносы точно должны быть
        lines.append(f"переносов: {res.hyphens}, шире лимита: {len(too_wide)}, "
                     f"строк со знаком в начале: {len(bad_start)}")
    except Exception:
        ok = False
        lines.append(traceback.format_exc())
    lines.append("ИТОГ: " + ("OK" if ok else "ОШИБКА"))
    (out / "selftest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if ok else 1


def run_smoke_gui(out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines, ok = [], True
    try:
        from PySide6.QtWidgets import QApplication

        from .gui import MainWindow
        from .settings import Settings

        app = QApplication.instance() or QApplication(sys.argv[:1])
        font = Path(tempfile.mkdtemp()) / "заглушка.gfont"
        font.write_bytes(build_gfont(synthetic_font()))
        s = Settings(font_path=str(font), line_mm=1000, margin_pct=0, calib_text="аа",
                     calib_mm=200, gap=0, space=100)
        w = MainWindow(settings=s, persist=False)
        w.resize(1200, 760)
        w.show()
        w.ed_in.setPlainText("Тест программирование")
        w.recompute()
        on = list(w.result.lines)
        w.cb_hyph.setChecked(False)
        w.recompute()
        off = list(w.result.lines)
        w.cb_hyph.setChecked(True)
        w.ed_in.setPlainText(SAMPLE)
        w.recompute()
        w.tabs.setCurrentIndex(1)
        app.processEvents()
        w.grab().save(str(out / "window.png"))
        lines.append(f"переносы вкл:  {on}")
        lines.append(f"переносы выкл: {off}")
        ok = on == ["Тест про-", "граммиро-", "вание"] and off == ["Тест", "программирование"]
        w.close()
    except Exception:
        ok = False
        lines.append(traceback.format_exc())
    lines.append("ИТОГ: " + ("OK" if ok else "ОШИБКА"))
    (out / "smoke.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if ok else 1
