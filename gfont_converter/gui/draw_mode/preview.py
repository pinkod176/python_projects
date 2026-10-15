"""Правая панель: символ в реальном размере и строка-тест в своём почерке.

Всё рисуется по штрихам .gfont — ровно тем, что попадёт в файл (сглаживание, шаг
точек, выравнивание, X по центру). Шаблон сюда не попадает. Ненарисованные символы
в строке показаны бледным системным шрифтом.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List, Optional

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy, QSlider,
                               QVBoxLayout, QWidget)

from gfont.normalize import TargetMetrics

from ..preview_widget import PreviewWidget
from .geometry import REF_XHEIGHT, REF_CAP
from .render import strokes_path


class GlyphRealSize(QWidget):
    """Один символ в масштабе строки предпросмотра."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.strokes: List = []
        self.tm = TargetMetrics()
        self.pen = 9.0
        self.zoom = 0.3
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(260, 190)

    def set_glyph(self, strokes, pen: float) -> None:
        self.strokes = strokes or []
        self.pen = pen
        self.update()

    def paintEvent(self, ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("white"))
        k = self.zoom
        tm = self.tm
        oy = self.height() * 0.72 - tm.baseline * k
        ox = self.width() / 2
        xh = tm.cap_height * REF_XHEIGHT / REF_CAP
        for yy, col in ((tm.baseline, QColor(240, 150, 150)), (tm.baseline - xh, QColor(160, 190, 240)),
                        (tm.baseline - tm.cap_height, QColor(210, 210, 210))):
            p.setPen(QPen(col, 1))
            p.drawLine(QPointF(0, oy + yy * k), QPointF(self.width(), oy + yy * k))
        if self.strokes:
            pen = QPen(QColor(20, 20, 25), max(1.0, self.pen * k))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawPath(strokes_path(self.strokes, ox, oy, k))
        else:
            p.setPen(QColor(150, 150, 150))
            p.drawText(self.rect(), Qt.AlignCenter, "символ ещё не нарисован")
        p.end()


class PreviewPanel(QWidget):
    textChanged = Signal(str)
    penChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        t = QLabel("Предпросмотр")
        f = t.font()
        f.setBold(True)
        t.setFont(f)
        lay.addWidget(t)
        lay.addWidget(QLabel("Символ в реальном размере (как в файле):"))
        self.glyph = GlyphRealSize()
        lay.addWidget(self.glyph)
        row = QHBoxLayout()
        row.addWidget(QLabel("Толщина пера:"))
        self.sl_pen = QSlider(Qt.Horizontal)
        self.sl_pen.setRange(1, 30)
        self.sl_pen.setValue(9)
        self.sl_pen.setToolTip("Только для предпросмотра: толщину пера задаёт само приложение")
        self.lbl_pen = QLabel("9")
        self.lbl_pen.setMinimumWidth(24)
        row.addWidget(self.sl_pen, 1)
        row.addWidget(self.lbl_pen)
        lay.addLayout(row)
        lay.addWidget(QLabel("Проверочный текст:"))
        self.ed = QLineEdit()
        self.ed.setPlaceholderText("Введите текст — он сразу покажется вашим почерком")
        lay.addWidget(self.ed)
        self.line = PreviewWidget()
        self.line.pale_fallback = True
        self.line.empty_hint = "Введите текст выше"
        self.line.set_options(zoom=0.095, pen=9.0)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(self.line)
        sa.setStyleSheet("QScrollArea { background: white; }")
        lay.addWidget(sa, 1)
        hint = QLabel("Бледные буквы — ещё не нарисованы (показаны системным шрифтом). "
                      "Раскладка строки приблизительная: интервал считает само приложение.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        lay.addWidget(hint)
        self.sl_pen.valueChanged.connect(self._pen)
        self.ed.textChanged.connect(self.textChanged.emit)
        self.setMinimumWidth(280)

    def _pen(self, v: int) -> None:
        self.lbl_pen.setText(str(v))
        self.line.set_options(pen=float(v))
        self.glyph.pen = float(v)
        self.glyph.update()
        self.penChanged.emit(float(v))

    def pen(self) -> float:
        return float(self.sl_pen.value())

    def set_pen(self, v: float) -> None:
        self.sl_pen.setValue(int(round(v)))
        self._pen(self.sl_pen.value())

    def set_line(self, text: str, glyphs: Dict[str, Optional[list]]) -> None:
        objs = {ch: SimpleNamespace(strokes=s or []) for ch, s in glyphs.items()}
        self.line.set_result(text, objs, {}, TargetMetrics())
        self.line.set_options(pen=self.pen())
