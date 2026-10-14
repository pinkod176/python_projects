"""Смоук-тест GUI (offscreen): окно, загрузка шрифта, предпросмотр, сохранение, проверка."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_gui_smoke(tmp_path, test_font):
    from gui.selftest import run_gui_smoke
    code = run_gui_smoke(test_font, str(tmp_path))
    report = (tmp_path / "smoke.txt").read_text(encoding="utf-8")
    assert code == 0, report
    assert "RESULT: OK" in report
    for name in ("screen_preview.png", "screen_glyphs.png", "screen_saved.png"):
        assert (tmp_path / name).stat().st_size > 10000


def test_engine_selftest(tmp_path, test_font):
    from gui.selftest import run_engine_selftest
    code = run_engine_selftest(test_font, str(tmp_path))
    assert code == 0, (tmp_path / "selftest.txt").read_text(encoding="utf-8")


def test_cancel_variants(tmp_path, test_font):
    """«Отмена» во время пакетной генерации: окно живо, недописанных файлов нет."""
    import tempfile
    import time
    from pathlib import Path

    os.environ["GFONT_NO_DIALOGS"] = "1"
    from PySide6.QtWidgets import QApplication

    from gfont.session import UiParams, variant_paths
    from gui.main_window import MainWindow
    from gui.settings import AppSettings

    app = QApplication.instance() or QApplication([])
    w = MainWindow(AppSettings(Path(tempfile.mkdtemp()) / "s.json"))
    try:
        w.load_font(test_font)
        t0 = time.time()
        while w.session is None and time.time() - t0 < 60:
            app.processEvents()
            time.sleep(0.01)
        w.session.cache.clear()            # холодный кэш — операция заведомо долгая
        cancelled = []
        paths = variant_paths(tmp_path, w.session.family, 3)
        task = w.start_variants(paths, UiParams(charset_preset="full", liveliness=0.5))
        task.cancelled.connect(lambda: cancelled.append(1))
        t0 = time.time()
        while time.time() - t0 < 0.5:
            app.processEvents()
            time.sleep(0.01)
        w.cancel_task()
        t0 = time.time()
        while task.isRunning() and time.time() - t0 < 120:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        assert not task.isRunning()
        assert cancelled, "сигнал отмены не пришёл"
        assert not any(p.exists() for p in paths[1:])
        assert not list(tmp_path.glob("*.tmp"))
        assert w.btn_save.isEnabled()      # окно снова готово к работе
    finally:
        w.close()
        app.processEvents()


def test_calibration_from_gui(tmp_path):
    import tempfile
    import time
    from pathlib import Path

    os.environ["GFONT_NO_DIALOGS"] = "1"
    from PySide6.QtWidgets import QApplication

    from gfont.validate import validate_file
    from gui.main_window import MainWindow
    from gui.settings import AppSettings

    app = QApplication.instance() or QApplication([])
    w = MainWindow(AppSettings(Path(tempfile.mkdtemp()) / "s.json"))
    try:
        out = tmp_path / "калибровка тест.gfont"
        task = w.start_calibration(out)
        t0 = time.time()
        while (task.isRunning() or not w.last_saved) and time.time() - t0 < 60:
            app.processEvents()
            time.sleep(0.01)
        assert out.exists()
        assert validate_file(str(out)).total > 1000
        assert "Калибровочный файл" in w.log.toPlainText()
    finally:
        w.close()
        app.processEvents()
