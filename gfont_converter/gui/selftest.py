"""Самопроверки, которые можно запустить и в собранном exe.

    GfontConverter.exe --selftest  ШРИФТ.ttf ПАПКА   — движок без окна
    GfontConverter.exe --smoke-gui ШРИФТ.ttf ПАПКА   — окно (offscreen): загрузка шрифта,
                                                      предпросмотр, сохранение, проверка, скриншоты

Результат пишется в ПАПКА/selftest.txt или ПАПКА/smoke.txt (у --windowed exe нет консоли),
код выхода 0 — успех.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path


def _write(path: Path, lines) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_engine_selftest(font: str, outdir: str) -> int:
    out = Path(outdir)
    lines = [f"python: {sys.version.split()[0]} frozen={getattr(sys, 'frozen', False)}",
             f"exe: {sys.executable}"]
    ok = False
    try:
        from gfont.format import read_gfont
        from gfont.session import FontSession, UiParams, default_template_path
        tpl = default_template_path()
        lines.append(f"встроенный шаблон: {tpl} существует={tpl.exists()}")
        gf = read_gfont(tpl)
        lines.append(f"шаблон прочитан: {len(gf.entries)} записей, префикс {len(gf.prefix)}")
        s = FontSession(font)
        lines.append(f"шрифт: {s.family}, символов {s.glyph_count}")
        target = out / "проверка шаблон с_клода" / f"{s.family}_1.gfont"
        rep = s.convert(UiParams(charset_preset="ru_en"), target, tpl, log=lambda *a: None)
        lines.append(rep.text())
        ok = rep.validation.ok and target.exists()
    except Exception:  # noqa: BLE001
        lines.append(traceback.format_exc())
    lines.append("RESULT: " + ("OK" if ok else "FAIL"))
    _write(out / "selftest.txt", lines)
    return 0 if ok else 1


def run_gui_smoke(font: str, outdir: str, timeout: float = 240.0) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["GFONT_NO_DIALOGS"] = "1"
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    ok = False
    w = app = None
    try:
        import tempfile

        from PySide6.QtWidgets import QApplication

        from gfont.validate import validate_file

        from .main_window import MainWindow
        from .settings import AppSettings

        app = QApplication.instance() or QApplication(sys.argv[:1])
        st = AppSettings(Path(tempfile.mkdtemp()) / "settings.json")
        w = MainWindow(st)
        w.resize(1400, 900)
        w.show()

        def wait(cond, secs, what):
            t0 = time.time()
            while not cond():
                app.processEvents()
                time.sleep(0.01)
                if time.time() - t0 > secs:
                    raise TimeoutError(f"не дождались: {what}")

        w.load_font(font)
        wait(lambda: w.session is not None, 60, "загрузка шрифта")
        lines.append(f"шрифт загружен: {w.session.family}, символов {w.session.glyph_count}")
        wait(lambda: bool(w.preview.glyphs), 120, "предпросмотр")
        lines.append(f"предпросмотр: {len(w.preview.glyphs)} символов")
        w.grab().save(str(out / "screen_preview.png"))
        w.tabs.setCurrentIndex(1)
        wait(lambda: len(w.grid.results) >= min(40, len(w.grid.items)), 120, "анализ символов")
        code = ord("щ") if ord("щ") in w.grid.results else next(iter(w.grid.results))
        w.grid.setCurrentItem(w.grid.items[code])
        app.processEvents()
        w.grab().save(str(out / "screen_glyphs.png"))
        w.tabs.setCurrentIndex(0)
        target = out / "смоук тест" / f"{w.session.family}_1.gfont"
        task = w.start_save(target)
        wait(lambda: not task.isRunning() and w.last_saved, timeout, "сохранение")
        rep = validate_file(str(target))
        app.processEvents()
        w.grab().save(str(out / "screen_saved.png"))
        lines.append(f"сохранено: {target}")
        lines.append(rep.summary())
        ok = rep.ok
    except Exception:  # noqa: BLE001
        lines.append(traceback.format_exc())
    finally:
        try:
            w.close()
            app.processEvents()
        except Exception:  # noqa: BLE001
            pass
    lines.append("RESULT: " + ("OK" if ok else "FAIL"))
    _write(out / "smoke.txt", lines)
    return 0 if ok else 1
