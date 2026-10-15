"""Общие функции рисования: штрихи .gfont, миниатюры, цвета светлой/тёмной темы."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap

from gfont.normalize import TargetMetrics

Point = Tuple[float, float]

STATUS_COLORS = {"drawn": QColor(60, 160, 90), "auto": QColor(70, 130, 210),
                 "skipped": QColor(150, 150, 150), "empty": QColor(0, 0, 0, 0)}


class Colors:
    def __init__(self, dark: bool):
        self.dark = dark
        if dark:
            self.bg = QColor(38, 38, 42)
            self.paper = QColor(52, 52, 58)
            self.border = QColor(90, 90, 100)
            self.ink = QColor(235, 235, 240)
            self.template = QColor(205, 205, 215)
            self.hint = QColor(150, 190, 255)
            self.base = QColor(220, 120, 120)
            self.xline = QColor(110, 150, 220)
            self.capline = QColor(140, 140, 150)
            self.extra = QColor(110, 110, 120)
            self.text = QColor(170, 170, 180)
        else:
            self.bg = QColor(232, 232, 236)
            self.paper = QColor(255, 254, 248)
            self.border = QColor(200, 200, 205)
            self.ink = QColor(25, 25, 35)
            self.template = QColor(95, 95, 105)
            self.hint = QColor(60, 110, 210)
            self.base = QColor(232, 140, 140)
            self.xline = QColor(105, 145, 230)
            self.capline = QColor(185, 185, 190)
            self.extra = QColor(215, 215, 220)
            self.text = QColor(120, 120, 130)
        self.start = QColor(40, 170, 80)
        self.arrow = QColor(230, 120, 30)


def strokes_path(strokes: Sequence[Sequence[Point]], ox: float, oy: float, k: float) -> QPainterPath:
    path = QPainterPath()
    for s in strokes:
        if not s:
            continue
        x, y = s[0]
        path.moveTo(ox + x * k, oy + y * k)
        if len(s) == 1:
            path.lineTo(ox + x * k + 0.01, oy + y * k)
        for x, y in s[1:]:
            path.lineTo(ox + x * k, oy + y * k)
    return path


def thumb_pixmap(strokes_g: Optional[List[List[Point]]], ch: str, status: str, size: int,
                 dark: bool, auto: bool = False, tm: Optional[TargetMetrics] = None) -> QPixmap:
    """Миниатюра символа: нарисованный глиф или бледный символ системного шрифта."""
    tm = tm or TargetMetrics()
    c = Colors(dark)
    pm = QPixmap(size, size)
    pm.fill(c.paper)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    k = size / 640.0
    oy = size * 0.70 - tm.baseline * k
    ox = size / 2
    if strokes_g:
        pen = QPen(c.ink, max(1.2, 11 * k))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPath(strokes_path(strokes_g, ox, oy, k))
    else:
        f = QFont()
        f.setPixelSize(int(size * 0.5))
        p.setFont(f)
        col = QColor(c.text)
        col.setAlpha(110 if status != "skipped" else 60)
        p.setPen(col)
        p.drawText(QRectF(0, 0, size, size * 0.92), Qt.AlignCenter, ch)
    mark = "auto" if (status == "drawn" and auto) else status
    if mark in ("drawn", "auto", "skipped"):
        p.setPen(Qt.NoPen)
        p.setBrush(STATUS_COLORS[mark])
        r = max(4.0, size * 0.09)
        p.drawEllipse(QPointF(size - r - 2, r + 2), r, r)
        if mark == "skipped":
            p.setPen(QPen(STATUS_COLORS["skipped"], max(1.0, size * 0.03)))
            p.drawLine(QPointF(size * 0.25, size * 0.85), QPointF(size * 0.75, size * 0.85))
    p.setPen(QPen(c.border, 1))
    p.setBrush(Qt.NoBrush)
    p.drawRect(QRectF(0.5, 0.5, size - 1, size - 1))
    p.end()
    return pm
