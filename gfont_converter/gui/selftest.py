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


SMOKE_DRAW_CHARS = "аАрй5,‑@"


def run_draw_smoke(outdir: str, timeout: float = 120.0) -> int:
    """Режим рисования без человека: штрихи настоящими событиями мыши по осевым линиям
    образца, заполнение из похожих, экспорт в .gfont, самопроверка, повторное открытие.
    Скриншоты холста с шаблоном — для «а», «А», «р», «й», «5», «,», «‑», «@» и строки."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["GFONT_NO_DIALOGS"] = "1"
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    ok = False
    w = app = None
    try:
        import tempfile

        import numpy as np
        from PySide6.QtWidgets import QApplication

        from gfont.validate import validate_file

        from .draw_mode.export import ExportOptions, import_gfont
        from .draw_mode.project import Project
        from .draw_mode.window import DrawWindow
        from .settings import AppSettings

        tmp = Path(tempfile.mkdtemp())
        old_appdata = os.environ.get("APPDATA")
        os.environ["APPDATA"] = str(tmp / "appdata")        # черновики — во временную папку
        app = QApplication.instance() or QApplication(sys.argv[:1])
        st = AppSettings(tmp / "settings.json")
        w = DrawWindow(st, restore_draft=False)
        w.resize(1500, 950)
        w.show()
        app.processEvents()
        cv = w.canvas
        lines.append(f"холст: {cv.width()}x{cv.height()} px, образец: {w.provider.source_name}")

        def wait(cond, secs, what):
            t0 = time.time()
            while not cond():
                app.processEvents()
                time.sleep(0.01)
                if time.time() - t0 > secs:
                    raise TimeoutError(f"не дождались: {what}")

        def draw_like_sample(code: int, wobble: float = 1.2, seed: int = 0) -> int:
            """Нарисовать символ мышью по осевой линии образца (с лёгким дрожанием руки)."""
            w.go_to(code)
            h = w.provider.hint(code, w.project.geometry())
            if h is None:
                return 0
            rng = np.random.default_rng([seed, code])
            n = 0
            for q, dot in zip(h.lines, h.dots):
                if dot or len(q) < 2:
                    cv.simulate_stroke([tuple(q[0])])
                else:
                    seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
                    t = np.concatenate([[0], np.cumsum(seg)])
                    s = np.linspace(0, t[-1], max(8, int(t[-1] / 4)))
                    pts = np.stack([np.interp(s, t, q[:, 0]), np.interp(s, t, q[:, 1])], axis=1)
                    pts += rng.normal(0, wobble, pts.shape)
                    cv.simulate_stroke([tuple(p) for p in pts])
                n += 1
            app.processEvents()
            return n

        # 1) холст с шаблоном (до рисования) — по одному снимку на символ
        w.ch_order.setChecked(False)
        for ch in SMOKE_DRAW_CHARS:
            w.go_to(ord(ch))
            app.processEvents()
            cv.grab().save(str(out / f"canvas_template_U+{ord(ch):04X}.png"))
        w.go_to(ord("й"))
        w.ch_order.setChecked(True)
        app.processEvents()
        cv.grab().save(str(out / "canvas_order_U+0439.png"))
        w.ch_order.setChecked(False)

        # 2) рисуем мышью
        text = "Съешь же ещё этих мягких булок, да выпей чаю! 2025"
        todo = [c for c in dict.fromkeys(text + SMOKE_DRAW_CHARS + "-иеNo") if not c.isspace()]
        total = 0
        for i, ch in enumerate(todo):
            total += draw_like_sample(ord(ch), seed=i)
        lines.append(f"нарисовано мышью: {len(todo)} символов, {total} штрихов")
        u, a, t = w.project.counts()
        lines.append(f"прогресс: {w.browser.bar.text()}")
        if u < len(todo) - 2:
            raise RuntimeError(f"нарисовано меньше, чем ожидалось: {u}")
        # отмена/повтор
        w.go_to(ord("а"))
        before = len(cv.strokes())
        cv.undo()
        cv.redo()
        if len(cv.strokes()) != before:
            raise RuntimeError("отмена/повтор не вернули штрихи")
        for ch in "аАрй5,@":
            w.go_to(ord(ch))
            app.processEvents()
            cv.grab().save(str(out / f"canvas_drawn_U+{ord(ch):04X}.png"))

        # 3) заполнение из похожих (ё из е, № из N+o, ‑ из -)
        from .draw_mode.fill import similar_candidates
        w._review(similar_candidates(w.project, w.missing_codes()), "из похожих")
        lines.append(f"после заполнения из похожих: {w.browser.bar.text()}")

        # 4) предпросмотр строки
        w.preview.ed.setText("Съешь же ещё этих мягких французских булок, да выпей чаю! №5 — ок")
        app.processEvents()
        w._refresh_preview()
        app.processEvents()
        w.preview.grab().save(str(out / "preview_line.png"))
        w.grab().save(str(out / "draw_window.png"))

        # 5) проект: сохранить и открыть снова
        proj_path = tmp / "мой почерк.gfproj"
        if not w._save_to(proj_path):
            raise RuntimeError("проект не сохранился")
        again = Project.load(proj_path)
        if again.counts() != w.project.counts():
            raise RuntimeError("проект после открытия отличается")

        # 6) экспорт (в фоне) и проверка
        target = out / "смоук рисование" / "мой почерк.gfont"
        task = w.start_export(ExportOptions(str(target)))
        wait(lambda: task is not None and not task.isRunning() and w.last_export is not None,
             timeout, "экспорт")
        res = w.last_export
        lines.append(res.text())
        rep = validate_file(str(target))
        lines.append("повторная самопроверка: " + ("OK" if rep.ok else "ОШИБКИ"))
        pr = Project()
        got = import_gfont(target, pr)
        lines.append(f"файл открыт в редакторе: {len(got)} символов")
        ok = rep.ok and len(got) >= u
    except Exception:  # noqa: BLE001
        lines.append(traceback.format_exc())
    finally:
        try:
            w.close()
            app.processEvents()
        except Exception:  # noqa: BLE001
            pass
        if "old_appdata" in locals():
            if old_appdata is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = old_appdata
    lines.append("RESULT: " + ("OK" if ok else "FAIL"))
    _write(out / "smoke_draw.txt", lines)
    return 0 if ok else 1
