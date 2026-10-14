"""Предпросмотр строки ПО ШТРИХАМ из конвертации (как будет в приложении).

Раскладка приблизительная: ширина символа = ширина bbox + зазор. Как интервал
считает настоящее приложение — неизвестно (см. «О программе» и калибровку).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from gfont.normalize import TargetMetrics

GAP = 35.0          # зазор между буквами в предпросмотре, ед. .gfont
SPACE = 110.0       # ширина пробела
LINE_H = 620.0      # высота строки
TOP = 470.0         # от верха строки до y = 0


def strokes_path(strokes, ox: float, oy: float, k: float) -> QPainterPath:
    path = QPainterPath()
    for s in strokes:
        if len(s) < 2:
            continue
        x, y = s[0]
        path.moveTo(ox + x * k, oy + y * k)
        for x, y in s[1:]:
            path.lineTo(ox + x * k, oy + y * k)
    return path


def outline_path(contours, ox: float, oy: float, k: float) -> QPainterPath:
    path = QPainterPath()
    path.setFillRule(Qt.WindingFill)
    for c in contours:
        if len(c) < 3:
            continue
        path.moveTo(ox + c[0][0] * k, oy + c[0][1] * k)
        for x, y in c[1:]:
            path.lineTo(ox + x * k, oy + y * k)
        path.closeSubpath()
    return path


class PreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ""
        self.glyphs: Dict[str, object] = {}
        self.outlines: Dict[str, list] = {}
        self.tm = TargetMetrics()
        self.pen = 9.0
        self.zoom = 0.16
        self.show_guides = True
        self.show_source = False
        self.busy = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(160)
        self.setAutoFillBackground(False)

    # ---- данные ----
    def set_result(self, text: str, glyphs: dict, outlines: dict, tm: TargetMetrics) -> None:
        self.text = text
        self.glyphs = glyphs
        self.outlines = outlines
        self.tm = tm
        self.busy = False
        self._fit_height()
        self.update()

    def _fit_height(self) -> None:
        self.setMinimumHeight(max(160, self.heightForWidth(max(self.width(), 300))))

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        self._fit_height()

    def set_options(self, *, pen=None, guides=None, source=None, zoom=None) -> None:
        if pen is not None:
            self.pen = pen
        if guides is not None:
            self.show_guides = guides
        if source is not None:
            self.show_source = source
        if zoom is not None:
            self.zoom = zoom
        self._fit_height()
        self.update()

    # ---- раскладка ----
    def _layout(self, width_px: float):
        k = self.zoom
        max_w = max(200.0, width_px / k - 60)
        lines: List[List[tuple]] = [[]]
        x = 30.0
        for word in self.text.split(" "):
            items = []
            wx = 0.0
            for ch in word:
                r = self.glyphs.get(ch)
                if r is None or not r.strokes:
                    items.append((ch, wx, 120.0, None))
                    wx += 120.0 + GAP
                    continue
                xs = [p[0] for s in r.strokes for p in s]
                x0, x1 = min(xs), max(xs)
                w = max(x1 - x0, 1.0)
                items.append((ch, wx - x0, w, r))
                wx += w + GAP
            if x + wx > max_w and lines[-1]:
                lines.append([])
                x = 30.0
            lines[-1].extend((ch, x + dx, w, r) for ch, dx, w, r in items)
            x += wx + SPACE
        return lines

    def sizeHint(self) -> QSize:
        return QSize(900, 300)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        n = len(self._layout(w)) if self.text else 1
        return int(n * LINE_H * self.zoom + 20)

    # ---- рисование ----
    def paintEvent(self, ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("white"))
        k = self.zoom
        tm = self.tm
        lines = self._layout(self.width()) if self.text else []
        pen = QPen(QColor(20, 20, 25), max(1.0, self.pen * k))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        for li, items in enumerate(lines):
            oy = 10 + (li * LINE_H + TOP) * k
            if self.show_guides:
                for yy, col in ((tm.baseline, QColor(240, 150, 150)),
                                (tm.baseline - 220.0, QColor(160, 190, 240)),
                                (tm.baseline - tm.cap_height, QColor(200, 200, 200))):
                    p.setPen(QPen(col, 1))
                    p.drawLine(QPointF(0, oy + yy * k), QPointF(self.width(), oy + yy * k))
            for ch, ox, w, r in items:
                ox_px = ox * k
                if r is None or not r.strokes:
                    p.setPen(QPen(QColor(220, 0, 0), 1.5))
                    p.setBrush(Qt.NoBrush)
                    p.drawRect(QRectF(ox_px, oy + (tm.baseline - tm.cap_height) * k,
                                      w * k, tm.cap_height * k))
                    continue
                if self.show_source and ch in self.outlines:
                    p.setPen(Qt.NoPen)
                    p.setBrush(QBrush(QColor(120, 170, 255, 70)))
                    p.drawPath(outline_path(self.outlines[ch], ox_px, oy, k))
                p.setBrush(Qt.NoBrush)
                p.setPen(pen)
                p.drawPath(strokes_path(r.strokes, ox_px, oy, k))
        if self.busy:
            p.setPen(QColor(120, 120, 120))
            p.drawText(self.rect().adjusted(8, 4, -8, -4), Qt.AlignRight | Qt.AlignTop,
                       "обновление…")
        if not self.text:
            p.setPen(QColor(140, 140, 140))
            p.drawText(self.rect(), Qt.AlignCenter,
                       "Откройте шрифт (кнопка «Открыть…» или перетащите .ttf/.otf в окно)")
        p.end()
