"""Холст рисования одного символа.

Слои снизу вверх: клетка («бумага») -> линии тетради -> шаблон-подсказка (пунктир,
отдельный слой: не входит в штрихи и экспорт) -> осевая линия с порядком (если включено)
-> штрихи пользователя (уже обработанные: так они попадут в файл) с номерами,
началом (зелёная точка) и стрелкой направления на конце.

Мышь/перо/тачпад: левая кнопка — штрих; отпустили — штрих готов. Клик без движения — точка.
Колесо — масштаб, пробел + перетаскивание или средняя кнопка — сдвиг холста.
Инструмент «Правка точек»: перетаскивание точки штриха; правая кнопка — удалить штрих.
Давление пера не используется (в формате толщина постоянная): события планшета Qt
превращает в обычные события мыши.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QApplication, QSizePolicy, QWidget

from .geometry import CellGeometry
from .editor import GlyphEditor, processed_cell
from .project import GlyphEntry, Project, Stroke
from .render import Colors
from .template import TemplateProvider

TEMPLATE_PEN = 2.4               # ширина пунктира шаблона, ед. клетки
TEMPLATE_DASH = [4.0, 2.7]       # штрих/пробел в ширинах пера (≈ 6 px / 4 px при подгонке под окно)
DOT_PX = 3.0                     # движение меньше этого (px) — точка


class DrawCanvas(QWidget):
    strokesChanged = Signal(int)          # код символа
    zoomChanged = Signal(float)

    def __init__(self, provider: TemplateProvider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.project: Optional[Project] = None
        self.ed = GlyphEditor()
        self.tool = "draw"                # draw | edit
        self.colors = Colors(False)
        self._scale = 0.6
        self._off = QPointF(0, 0)
        self._auto_fit = True
        self._raw: Optional[List[Tuple[float, float]]] = None
        self._raw_px = 0.0
        self._last_px: Optional[QPointF] = None
        self._pan_from: Optional[QPointF] = None
        self._space = False
        self._drag: Optional[Tuple[int, int]] = None
        self._proc: Optional[List[np.ndarray]] = None
        self.setMinimumSize(600, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(False)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setCursor(Qt.CrossCursor)

    # ------------------------------------------------------------ данные
    @property
    def code(self) -> int:
        return self.ed.code

    @property
    def variant(self) -> int:
        return self.ed.variant

    def set_project(self, project: Project) -> None:
        self.project = project
        self.ed.set_project(project)
        self.invalidate()

    def set_code(self, code: int, variant: int = 0) -> None:
        self.ed.select(code, variant)
        self._raw = None
        self._drag = None
        self.invalidate()

    def set_dark(self, dark: bool) -> None:
        self.colors = Colors(dark)
        self.update()

    def geo(self) -> CellGeometry:
        return self.project.geometry() if self.project else CellGeometry()

    def entry(self) -> GlyphEntry:
        return self.ed.entry()

    def strokes(self) -> List[Stroke]:
        return self.ed.strokes() if self.project else []

    def invalidate(self) -> None:
        self._proc = None
        self.update()

    def processed(self) -> List[np.ndarray]:
        """Обработанные штрихи текущего символа в единицах клетки (как будут в файле)."""
        if self._proc is None:
            self._proc = processed_cell(self.strokes(), self.project) if self.project else []
        return self._proc

    # ------------------------------------------------------------ правка (общий GlyphEditor)
    def _changed(self) -> None:
        self.invalidate()
        self.strokesChanged.emit(self.code)

    def can_undo(self) -> bool:
        return self.ed.can_undo()

    def can_redo(self) -> bool:
        return self.ed.can_redo()

    def undo(self) -> None:
        if self.ed.undo():
            self._changed()

    def redo(self) -> None:
        if self.ed.redo():
            self._changed()

    def add_stroke(self, s: Stroke) -> None:
        self.ed.add_stroke(s)
        self._changed()

    def delete_last(self) -> None:
        if self.ed.delete_last():
            self._changed()

    def clear_glyph(self) -> None:
        if self.ed.clear():
            self._changed()

    def delete_stroke(self, i: int) -> None:
        if self.ed.delete_stroke(i):
            self._changed()

    def replace_glyph(self, entry: GlyphEntry) -> None:
        """Заменить символ целиком (заполнение, импорт) с возможностью отмены."""
        self.ed.replace(entry)
        self._changed()

    # ------------------------------------------------------------ вид
    def view(self) -> QTransform:
        return QTransform(self._scale, 0, 0, self._scale, self._off.x(), self._off.y())

    def to_cell(self, pos: QPointF) -> Tuple[float, float]:
        return ((pos.x() - self._off.x()) / self._scale, (pos.y() - self._off.y()) / self._scale)

    def to_widget(self, x: float, y: float) -> QPointF:
        return QPointF(self._off.x() + x * self._scale, self._off.y() + y * self._scale)

    def fit(self) -> None:
        geo = self.geo()
        m = 12
        w, h = max(50, self.width() - 2 * m), max(50, self.height() - 2 * m)
        self._scale = min(w / geo.width, h / geo.height)
        self._off = QPointF((self.width() - geo.width * self._scale) / 2,
                            (self.height() - geo.height * self._scale) / 2)
        self._auto_fit = True
        self.zoomChanged.emit(self._scale)
        self.update()

    def zoom_by(self, f: float, at: Optional[QPointF] = None) -> None:
        at = at or QPointF(self.width() / 2, self.height() / 2)
        new = min(8.0, max(0.1, self._scale * f))
        f = new / self._scale
        self._off = at + (self._off - at) * f
        self._scale = new
        self._auto_fit = False
        self.zoomChanged.emit(self._scale)
        self.update()

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        if self._auto_fit:
            self.fit()

    # ------------------------------------------------------------ рисование
    def paintEvent(self, ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = self.colors
        p.fillRect(self.rect(), c.bg)
        if self.project is None:
            p.end()
            return
        geo = self.geo()
        st = self.project.settings
        p.setTransform(self.view())
        cell = QRectF(0, 0, geo.width, geo.height)
        p.fillRect(cell, c.paper)
        p.setPen(QPen(c.border, 1.0 / self._scale))
        p.drawRect(cell)

        if st.show_guides:
            self._paint_guides(p, geo)
        if st.show_template:
            self._paint_template(p, geo)
        if st.show_order:
            self._paint_hint(p, geo)
        self._paint_strokes(p, geo)

        p.resetTransform()
        f = QFont()
        f.setPixelSize(13)
        p.setFont(f)
        p.setPen(c.text)
        tl = self.to_widget(8, 6)
        p.drawText(QRectF(tl.x(), tl.y(), 400, 20), Qt.AlignLeft | Qt.AlignTop,
                   f"{chr(self.code)}   U+{self.code:04X}   вариант {self.variant + 1}")
        p.end()

    def _paint_guides(self, p: QPainter, geo: CellGeometry) -> None:
        c = self.colors
        px = 1.0 / self._scale
        styles = {"asc": (c.extra, 1.0, Qt.DashLine), "cap": (c.capline, 1.0, Qt.SolidLine),
                  "x": (c.xline, 1.5, Qt.SolidLine), "base": (c.base, 1.8, Qt.SolidLine),
                  "desc": (c.extra, 1.0, Qt.DashLine)}
        for name, y in geo.guides():
            col, w, style = styles[name]
            pen = QPen(col, w * px)
            pen.setStyle(style)
            p.setPen(pen)
            p.drawLine(QPointF(0, y), QPointF(geo.width, y))

    def _template_pen(self, color: QColor) -> QPen:
        pen = QPen(color, TEMPLATE_PEN)
        pen.setDashPattern(TEMPLATE_DASH)
        pen.setCapStyle(Qt.FlatCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def _paint_template(self, p: QPainter, geo: CellGeometry) -> None:
        shape = self.provider.shape(self.code, geo)
        if shape is None:
            return
        st = self.project.settings
        p.save()
        p.setOpacity(max(0.05, min(1.0, st.template_opacity)))
        p.setBrush(Qt.NoBrush)
        p.setPen(self._template_pen(self.colors.template))
        if shape.kind == "box":
            p.drawRect(shape.rect)
            f = QFont()
            f.setPixelSize(max(8, int(shape.rect.height() * 0.6)))
            p.setFont(f)
            p.setPen(self.colors.template)
            p.drawText(shape.rect, Qt.AlignCenter, shape.label)
        else:
            p.drawPath(shape.path)
        p.restore()

    def _paint_hint(self, p: QPainter, geo: CellGeometry) -> None:
        h = self.provider.hint(self.code, geo)
        if h is None:
            return
        c = self.colors.hint
        p.save()
        p.setOpacity(max(0.35, min(1.0, self.project.settings.template_opacity + 0.3)))
        pen = QPen(c, 1.8)
        pen.setDashPattern([3.0, 3.0])
        f = QFont()
        f.setPixelSize(int(0.075 * geo.cap))
        f.setBold(True)
        p.setFont(f)
        for i, (q, dot) in enumerate(zip(h.lines, h.dots)):
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            if dot or len(q) < 2:
                p.drawEllipse(QPointF(*q[0]), 6, 6)
            else:
                path = QPainterPath(QPointF(*q[0]))
                for x, y in q[1:]:
                    path.lineTo(x, y)
                p.drawPath(path)
                self._arrow(p, q, c, 0.05 * geo.cap)
            self._badge(p, q[0], str(i + 1), c, 0.045 * geo.cap, filled=False)
        p.restore()

    def _arrow(self, p: QPainter, q: np.ndarray, color: QColor, size: float) -> None:
        if len(q) < 2:
            return
        end = q[-1]
        j = len(q) - 2
        while j > 0 and np.hypot(*(q[j] - end)) < size * 0.8:
            j -= 1
        d = end - q[j]
        n = math.hypot(*d)
        if n < 1e-6:
            return
        d = d / n
        nrm = np.array([-d[1], d[0]])
        tip = end + d * size * 0.35
        a = tip - d * size + nrm * size * 0.55
        b = tip - d * size - nrm * size * 0.55
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPolygon(QPolygonF([QPointF(*tip), QPointF(*a), QPointF(*b)]))
        p.restore()

    def _badge(self, p: QPainter, at, text: str, color: QColor, r: float, filled: bool = True) -> None:
        cx, cy = float(at[0]) - 1.6 * r, float(at[1]) - 1.6 * r
        p.save()
        p.setPen(QPen(color, max(1.0, r * 0.15)))
        p.setBrush(color if filled else self.colors.paper)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(self.colors.paper if filled else color)
        p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), Qt.AlignCenter, text)
        p.restore()

    def _paint_strokes(self, p: QPainter, geo: CellGeometry) -> None:
        c = self.colors
        st = self.project.settings
        w = st.pen / geo.k
        pen = QPen(c.ink, w)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        f = QFont()
        f.setPixelSize(int(0.055 * geo.cap))
        f.setBold(True)
        p.setFont(f)
        procs = self.processed()
        for q in procs:
            if len(q) < 2:
                continue
            path = QPainterPath(QPointF(*q[0]))
            for x, y in q[1:]:
                path.lineTo(x, y)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        # начало, направление, номер — поверх всех штрихов
        for i, q in enumerate(procs):
            if len(q) < 2:
                continue
            p.setPen(Qt.NoPen)
            p.setBrush(c.start)
            p.drawEllipse(QPointF(*q[0]), 0.6 * w + 2, 0.6 * w + 2)
            if self.strokes()[i].dot is False:
                self._arrow(p, q, c.arrow, max(16.0, 1.6 * w))
            self._badge(p, q[0], str(i + 1), c.arrow, 0.04 * geo.cap)
            if self.tool == "edit":
                p.setBrush(c.paper)
                p.setPen(QPen(c.hint, 1.2 / self._scale))
                for x, y in q:
                    p.drawEllipse(QPointF(x, y), 4 / self._scale, 4 / self._scale)
        if self._raw and len(self._raw) >= 1:
            live = QPen(c.ink, w)
            live.setCapStyle(Qt.RoundCap)
            live.setJoinStyle(Qt.RoundJoin)
            col = QColor(c.ink)
            col.setAlpha(150)
            live.setColor(col)
            p.setPen(live)
            path = QPainterPath(QPointF(*self._raw[0]))
            for x, y in self._raw[1:]:
                path.lineTo(x, y)
            if len(self._raw) == 1:
                path.lineTo(self._raw[0][0] + 0.01, self._raw[0][1])
            p.drawPath(path)

    # ------------------------------------------------------------ мышь, перо, клавиши
    def tabletEvent(self, ev) -> None:
        # давление и наклон пера не используются: отказываемся от события,
        # и Qt присылает такое же событие мыши
        ev.ignore()

    def _nearest_point(self, pos: QPointF, max_px: float = 12.0) -> Optional[Tuple[int, int]]:
        best, arg = max_px, None
        for i, q in enumerate(self.processed()):
            for j, (x, y) in enumerate(q):
                d = math.hypot(self._off.x() + x * self._scale - pos.x(),
                               self._off.y() + y * self._scale - pos.y())
                if d < best:
                    best, arg = d, (i, j)
        return arg

    def _nearest_stroke(self, pos: QPointF, max_px: float = 14.0) -> Optional[int]:
        cx, cy = self.to_cell(pos)
        pt = np.array([[cx, cy]])
        best, arg = max_px / self._scale, None
        from gfont.stroke_order import _seg_dist
        for i, q in enumerate(self.processed()):
            if len(q) == 0:
                continue
            d = float(_seg_dist(pt, q).min())
            if d < best:
                best, arg = d, i
        return arg

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        self.setFocus()
        if self.project is None:
            return
        pos = ev.position()
        if ev.button() == Qt.MiddleButton or (ev.button() == Qt.LeftButton and self._space):
            self._pan_from = pos
            self.setCursor(Qt.ClosedHandCursor)
            return
        if ev.button() == Qt.RightButton:
            i = self._nearest_stroke(pos)
            if i is not None:
                self.delete_stroke(i)
            return
        if ev.button() != Qt.LeftButton:
            return
        if self.tool == "edit":
            hit = self._nearest_point(pos)
            if hit is not None:
                i, j = hit
                self.ed.begin_point_edit(i)
                self._drag = (i, j)
                self.invalidate()
            return
        self._raw = [self.to_cell(pos)]
        self._raw_px = 0.0
        self._last_px = pos
        self.update()

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        pos = ev.position()
        if self._pan_from is not None:
            self._off += pos - self._pan_from
            self._pan_from = pos
            self._auto_fit = False
            self.update()
            return
        if self._drag is not None:
            i, j = self._drag
            self.ed.move_point(i, j, *self.to_cell(pos))
            self._proc = None
            self.update()
            return
        if self._raw is not None:
            d = math.hypot(pos.x() - self._last_px.x(), pos.y() - self._last_px.y())
            if d >= 0.5:
                self._raw.append(self.to_cell(pos))
                self._raw_px += d
                self._last_px = pos
                self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if self._pan_from is not None and ev.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._pan_from = None
            self.setCursor(Qt.OpenHandCursor if self._space else Qt.CrossCursor)
            return
        if self._drag is not None and ev.button() == Qt.LeftButton:
            self._drag = None
            self._changed()
            return
        if self._raw is not None and ev.button() == Qt.LeftButton:
            raw, self._raw = self._raw, None
            if self._raw_px < DOT_PX:
                self.add_stroke(Stroke([raw[0]], dot=True))
            else:
                self.add_stroke(Stroke(raw))

    def wheelEvent(self, ev) -> None:
        dy = ev.angleDelta().y() or ev.pixelDelta().y()
        if dy:
            self.zoom_by(1.0015 ** dy, ev.position())

    def keyPressEvent(self, ev) -> None:
        if ev.key() == Qt.Key_Space and not ev.isAutoRepeat():
            self._space = True
            self.setCursor(Qt.OpenHandCursor)
            return
        super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev) -> None:
        if ev.key() == Qt.Key_Space and not ev.isAutoRepeat():
            self._space = False
            self._pan_from = None
            self.setCursor(Qt.CrossCursor)
            return
        super().keyReleaseEvent(ev)

    # ------------------------------------------------------------ для тестов
    def simulate_stroke(self, cell_points, button=Qt.LeftButton) -> None:
        """Нарисовать штрих настоящими событиями мыши (точки — в единицах клетки)."""
        pts = [self.to_widget(x, y) for x, y in cell_points]

        def send(t, pos, btn, buttons):
            gpos = QPointF(self.mapToGlobal(pos.toPoint()))
            QApplication.sendEvent(self, QMouseEvent(t, pos, gpos, btn, buttons, Qt.NoModifier))

        send(QEvent.MouseButtonPress, pts[0], button, button)
        for pt in pts[1:]:
            send(QEvent.MouseMove, pt, Qt.NoButton, button)
        send(QEvent.MouseButtonRelease, pts[-1], button, Qt.NoButton)
