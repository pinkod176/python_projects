"""Светлая и тёмная тема (стиль Fusion + палитра), общая для всего приложения."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

_default_style = None


def apply_theme(dark: bool) -> None:
    global _default_style
    app = QApplication.instance()
    if app is None:
        return
    if _default_style is None:
        _default_style = app.style().objectName()
    if not dark:
        app.setStyle(_default_style or "Fusion")
        app.setPalette(app.style().standardPalette())
        return
    app.setStyle("Fusion")
    p = QPalette()
    base, alt, text = QColor(45, 45, 50), QColor(55, 55, 62), QColor(230, 230, 235)
    p.setColor(QPalette.Window, QColor(38, 38, 42))
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Base, base)
    p.setColor(QPalette.AlternateBase, alt)
    p.setColor(QPalette.ToolTipBase, QColor(60, 60, 66))
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, QColor(55, 55, 62))
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.BrightText, QColor(255, 90, 90))
    p.setColor(QPalette.Highlight, QColor(70, 120, 200))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.Link, QColor(120, 170, 255))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor(120, 120, 128))
    app.setPalette(p)
