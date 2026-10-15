"""Запуск приложения и общий перехватчик необработанных исключений."""

from __future__ import annotations

import os
import sys
import threading
import traceback
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from gfont.session import resource_dir

from .settings import settings_dir

_window = None


def _write_crash_log(text: str) -> str:
    try:
        d = settings_dir()
        d.mkdir(parents=True, exist_ok=True)
        p = d / "error.log"
        with p.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n{text}\n")
        return str(p)
    except OSError:
        return ""


def _report(text: str) -> None:
    log_path = _write_crash_log(text)
    w = _window
    if w is not None:
        try:
            w.log_line("✖ Непредвиденная ошибка:\n" + text)
        except Exception:  # noqa: BLE001
            pass
    if os.environ.get("GFONT_NO_DIALOGS") or QApplication.instance() is None:
        sys.stderr.write(text)
        return
    msg = QMessageBox(QMessageBox.Critical, "Непредвиденная ошибка",
                      "Произошла ошибка. Программа продолжит работу.\n"
                      + (f"Подробности записаны в {log_path}" if log_path else ""))
    msg.setDetailedText(text)
    msg.exec()


def install_excepthook() -> None:
    def hook(etype, value, tb):
        if issubclass(etype, KeyboardInterrupt):
            sys.__excepthook__(etype, value, tb)
            return
        text = "".join(traceback.format_exception(etype, value, tb))
        # из чужого потока — показываем окно в GUI-потоке
        app = QApplication.instance()
        if app is not None and threading.current_thread() is not threading.main_thread():
            QTimer.singleShot(0, app, lambda: _report(text))
        else:
            _report(text)

    sys.excepthook = hook
    threading.excepthook = lambda a: hook(a.exc_type, a.exc_value, a.exc_traceback)


def run_app(argv) -> int:
    global _window
    app = QApplication.instance() or QApplication(list(argv))
    app.setApplicationName("GfontConverter")
    app.setOrganizationName("GfontConverter")
    icon = resource_dir() / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    install_excepthook()
    from .main_window import MainWindow
    _window = MainWindow()
    if _window.settings["dark_theme"]:
        from .draw_mode.theme import apply_theme
        apply_theme(True)
    _window.show()
    if "--draw" in argv:
        _window.open_draw_mode()
    # шрифт можно передать аргументом: GfontConverter.exe шрифт.ttf
    files = [a for a in argv[1:] if not a.startswith("-")]
    if files:
        _window.load_font(files[0])
    return app.exec()
