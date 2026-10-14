"""Сетка символов набора и крупный вид одного символа (точки, направление, номера штрихов)."""

from __future__ import annotations

import math
from typing import Dict, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF)
from PySide6.QtWidgets import QListView, QListWidget, QListWidgetItem, QWidget

from gfont.normalize import TargetMetrics

COLORS = [QColor(25, 25, 25), QColor(210, 40, 40), QColor(30, 100, 210), QColor(20, 150, 60),
          QColor(190, 100, 0), QColor(150, 20, 170), QColor(0, 150, 150)]
WARN_BG = QColor(255, 236, 200)
MISSING_BG = QColor(245, 245, 245)


def _fit(strokes, w: float, h: float, tm: TargetMetrics, margin: float = 6.0):
    """Масштаб и сдвиг: поле от верхнего выносного до нижнего, X по центру."""
    top = tm.baseline - 1.25 * tm.cap_height
    bottom = tm.baseline + 0.55 * tm.cap_height
    xs = [p[0] for s in strokes for p in s] or [0.0]
    half = max(abs(min(xs)), abs(max(xs)), 0.45 * (bottom - top))
    k = min((w - 2 * margin) / (2 * half), (h - 2 * margin) / (bottom - top))
    return k, w / 2.0, margin - top * k + (h - 2 * margin - (bottom - top) * k) / 2


def glyph_icon(strokes, warnings, tm: TargetMetrics, size: int = 56) -> QIcon:
    pm = QPixmap(size, size)
    missing = not strokes
    pm.fill(MISSING_BG if missing else (WARN_BG if warnings else QColor("white")))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if strokes:
        k, ox, oy = _fit(strokes, size, size, tm, 4)
        pen = QPen(QColor(20, 20, 20), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        for s in strokes:
            if len(s) >= 2:
                p.drawPolyline(QPolygonF([QPointF(ox + x * k, oy + y * k) for x, y in s]))
    if warnings:
        p.setPen(QColor(200, 110, 0))
        f = QFont()
        f.setPixelSize(14)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 0, size - 2, 16), Qt.AlignRight, "⚠" if strokes else "×")
    p.end()
    return QIcon(pm)


class GlyphGrid(QListWidget):
    glyphSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setIconSize(QSize(56, 56))
        self.setGridSize(QSize(74, 84))
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.items: Dict[int, QListWidgetItem] = {}
        self.results: Dict[int, object] = {}
        self.currentItemChanged.connect(self._changed)

    def reset_codes(self, codes, tm: TargetMetrics) -> None:
        self.clear()
        self.items.clear()
        self.results.clear()
        self.tm = tm
        blank = glyph_icon([], [], tm)
        for c in codes:
            it = QListWidgetItem(blank, f"{chr(c)}  {c:04X}")
            it.setData(Qt.UserRole, c)
            it.setToolTip(f"U+{c:04X} «{chr(c)}» — ещё не обработан")
            self.addItem(it)
            self.items[c] = it

    def update_glyph(self, r, tm: TargetMetrics) -> None:
        it = self.items.get(r.code)
        if it is None:
            return
        self.results[r.code] = r
        it.setIcon(glyph_icon(r.strokes, r.warnings, tm))
        n_pts = sum(len(s) for s in r.strokes)
        tip = f"U+{r.code:04X} «{chr(r.code)}»: штрихов {len(r.strokes)}, точек {n_pts}"
        if r.warnings:
            tip += "\n⚠ " + "; ".join(r.warnings)
        it.setToolTip(tip)
        if self.currentItem() is it:
            self.glyphSelected.emit(r.code)

    def warning_codes(self):
        return [c for c, r in self.results.items() if r.warnings]

    def _changed(self, cur, _prev) -> None:
        if cur is not None:
            self.glyphSelected.emit(int(cur.data(Qt.UserRole)))


class GlyphDetail(QWidget):
    """Крупный вид: цветные штрихи, все точки, зелёное начало, стрелки направления, номера."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.outline = None
        self.tm = TargetMetrics()
        self.setMinimumSize(320, 320)

    def set_glyph(self, result, tm: TargetMetrics, outline=None) -> None:
        self.result = result
        self.tm = tm
        self.outline = outline
        self.update()

    def paintEvent(self, ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("white"))
        r = self.result
        if r is None:
            p.setPen(QColor(140, 140, 140))
            p.drawText(self.rect(), Qt.AlignCenter, "Выберите символ в сетке слева")
            p.end()
            return
        tm = self.tm
        k, ox, oy = _fit(r.strokes, self.width(), self.height() - 40, tm, 20)
        oy += 30
        for yy, col, name in ((tm.baseline, QColor(240, 150, 150), "базовая"),
                              (tm.baseline - 220.0, QColor(160, 190, 240), "строчные"),
                              (tm.baseline - tm.cap_height, QColor(190, 190, 190), "заглавные")):
            p.setPen(QPen(col, 1, Qt.DashLine))
            p.drawLine(QPointF(0, oy + yy * k), QPointF(self.width(), oy + yy * k))
            p.drawText(QPointF(4, oy + yy * k - 3), name)
        if self.outline:
            path = QPainterPath()
            path.setFillRule(Qt.WindingFill)
            for c in self.outline:
                path.moveTo(ox + c[0][0] * k, oy + c[0][1] * k)
                for x, y in c[1:]:
                    path.lineTo(ox + x * k, oy + y * k)
                path.closeSubpath()
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(120, 170, 255, 60)))
            p.drawPath(path)
            p.setBrush(Qt.NoBrush)
        for i, s in enumerate(r.strokes):
            col = COLORS[i % len(COLORS)]
            pts = [QPointF(ox + x * k, oy + y * k) for x, y in s]
            p.setPen(QPen(col, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            if len(pts) >= 2:
                p.drawPolyline(QPolygonF(pts))
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            for q in pts:
                p.drawEllipse(q, 2.6, 2.6)
            # стрелки направления на каждом ~3-м отрезке
            for j in range(1, len(pts), 3):
                a, b = pts[j - 1], pts[j]
                dx, dy = b.x() - a.x(), b.y() - a.y()
                L = math.hypot(dx, dy)
                if L < 8:
                    continue
                ux, uy = dx / L, dy / L
                m = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
                head = QPolygonF([m + QPointF(ux * 6, uy * 6),
                                  m + QPointF(-ux * 4 - uy * 4, -uy * 4 + ux * 4),
                                  m + QPointF(-ux * 4 + uy * 4, -uy * 4 - ux * 4)])
                p.drawPolygon(head)
            if pts:
                p.setBrush(QColor(0, 180, 0))
                p.drawEllipse(pts[0], 5, 5)
                p.setPen(col)
                p.drawText(pts[0] + QPointF(7, -7), str(i + 1))
                p.setPen(Qt.NoPen)
            p.setBrush(Qt.NoBrush)
        n_pts = sum(len(s) for s in r.strokes)
        p.setPen(QColor(40, 40, 40))
        head = (f"U+{r.code:04X} «{chr(r.code)}» — штрихов: {len(r.strokes)}, точек: {n_pts}"
                if r.strokes else f"U+{r.code:04X} «{chr(r.code)}» — пусто")
        if r.src_code is not None and r.src_code != r.code:
            head += f" (подстановка U+{r.src_code:04X})"
        p.drawText(QRectF(8, 4, self.width() - 16, 20), Qt.AlignLeft, head)
        if r.warnings:
            p.setPen(QColor(190, 100, 0))
            p.drawText(QRectF(8, 22, self.width() - 16, 20), Qt.AlignLeft,
                       "⚠ " + "; ".join(r.warnings))
        p.end()
