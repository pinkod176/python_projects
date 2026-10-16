"""Окно утилиты: текст -> строки с переносами под ширину страницы плоттера."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from .gfont import GFontError, Strokes, read_gfont
from .layout import LayoutResult, wrap_text
from .metrics import Metrics, bbox
from .settings import Settings, load_settings, save_settings

SAMPLE = ("Программирование плоттера — интересное занятие. Подъезд, чайка, классный "
          "кто-то, объявление, 1234567, ООО, автор, обезьяна.")


def _spin(lo: float, hi: float, step: float, decimals: int = 1, suffix: str = "") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setSingleStep(step)
    s.setDecimals(decimals)
    if suffix:
        s.setSuffix(suffix)
    s.setKeyboardTracking(False)
    return s


def find_default_font() -> str:
    """Шрифт по умолчанию: первый .gfont в gcodeFonts рядом с программой или в текущей папке."""
    roots = [Path.cwd(), Path(sys.argv[0]).resolve().parent]
    for r in roots:
        for d in (r / "gcodeFonts", r.parent / "gcodeFonts", r):
            if d.is_dir():
                found = sorted(d.glob("*.gfont"))
                if found:
                    return str(found[0])
    return ""


class Preview(QWidget):
    """Строки результата, нарисованные штрихами шрифта, и граница строки."""

    def __init__(self):
        super().__init__()
        self.zoom = 0.22
        self.lines: List[str] = []
        self.glyphs: Dict[int, Strokes] = {}
        self.metrics: Optional[Metrics] = None
        self.limit = 0.0        # допустимая ширина (с запасом), ед. шрифта
        self.full = 0.0         # ширина строки без запаса
        self.top, self.bottom = -420.0, 60.0
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor("white"))
        self.setPalette(pal)

    def set_data(self, lines, glyphs, metrics, limit, full, avail_px: int = 0):
        self.lines, self.glyphs, self.metrics = lines, glyphs, metrics
        self.limit, self.full = limit, full
        if avail_px > 0 and full > 0:          # вся строка по ширине окна предпросмотра
            self.zoom = max(0.01, (avail_px - 70) / (full + 40))
        ys = [p[1] for c, st in glyphs.items() if 0x410 <= c <= 0x44F for s in st for p in s]
        if ys:
            self.top, self.bottom = min(ys) - 30, max(ys) + 30
        self.updateGeometry()
        self.adjustSize()
        self.update()

    def _line_h(self) -> float:
        return self.bottom - self.top

    def sizeHint(self) -> QSize:
        w = (self.full + 40) * self.zoom + 70
        h = (len(self.lines) * self._line_h() + 100) * self.zoom
        return QSize(int(w), int(max(h, 200)))

    def paintEvent(self, _ev):
        if self.metrics is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        z = self.zoom
        x0 = 40.0
        H = self.height()
        p.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        p.drawLine(QPointF(x0 + self.full * z, 0), QPointF(x0 + self.full * z, H))
        p.setPen(QPen(QColor(230, 60, 60), 1))
        p.drawLine(QPointF(x0 + self.limit * z, 0), QPointF(x0 + self.limit * z, H))
        p.drawLine(QPointF(x0, 0), QPointF(x0, H))
        pen = QPen(QColor(20, 20, 20), max(1.0, 9 * z))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        m = self.metrics
        for li, line in enumerate(self.lines):
            oy = 20 + (li * self._line_h() - self.top) * z
            x = 0.0
            prev = False
            for ch in line:
                if ch.isspace():
                    x += m.space
                    prev = False
                    continue
                if prev:
                    x += m.gap
                strokes = self.glyphs.get(ord(ch))
                if not strokes:
                    w = m.fallback
                    p.setPen(QPen(QColor(230, 0, 0), 1))
                    p.drawRect(QRectF(x0 + x * z, oy + (self.top + 40) * z, w * z,
                                      (-self.top - 100) * z))
                else:
                    gx0, gx1, _, _ = bbox(strokes)
                    w = max(gx1 - gx0, 1.0)
                    p.setPen(pen)
                    for s in strokes:
                        if len(s) < 2:
                            continue
                        path = QPainterPath(QPointF(x0 + (x + s[0][0] - gx0) * z, oy + s[0][1] * z))
                        for px, py in s[1:]:
                            path.lineTo(x0 + (x + px - gx0) * z, oy + py * z)
                        p.drawPath(path)
                x += w
                prev = True
        p.end()


class MainWindow(QMainWindow):
    def __init__(self, settings: Optional[Settings] = None, persist: bool = True):
        super().__init__()
        self.setWindowTitle("Переносы для плоттера")
        self.resize(1200, 760)
        self.persist = persist
        self.s = settings or load_settings()
        self.glyphs: Dict[int, Strokes] = {}
        self.metrics: Optional[Metrics] = None
        self.result: Optional[LayoutResult] = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.recompute)
        self._loading = False
        self._build()
        self._load_values()
        if not self.s.font_path or not Path(self.s.font_path).is_file():
            self.s.font_path = find_default_font()
        if self.s.font_path:
            self.load_font(self.s.font_path, quiet=True)
        self.recompute()

    # ---------------------------------------------------------------- UI
    def _build(self):
        root = QWidget()
        lay = QVBoxLayout(root)

        top = QHBoxLayout()
        top.addWidget(QLabel("Шрифт .gfont:"))
        self.font_edit = QLineEdit()
        self.font_edit.setReadOnly(True)
        top.addWidget(self.font_edit, 1)
        btn_font = QPushButton("Открыть…")
        btn_font.clicked.connect(self.choose_font)
        top.addWidget(btn_font)
        self.font_info = QLabel("")
        top.addWidget(self.font_info)
        lay.addLayout(top)

        row = QHBoxLayout()
        self.cb_hyph = QCheckBox("Переносы")
        self.cb_hyph.setToolTip("Выключено — слова переносятся целиком, как раньше")
        row.addWidget(self.cb_hyph)
        row.addSpacing(20)
        row.addWidget(QLabel("Ширина строки:"))
        self.sp_line = _spin(5, 5000, 1, 1, " мм")
        row.addWidget(self.sp_line)
        row.addWidget(QLabel("Запас:"))
        self.sp_margin = _spin(0, 30, 0.5, 1, " %")
        self.sp_margin.setToolTip("Строки делаются немного короче, чтобы программа плоттера\n"
                                  "не перенесла их ещё раз из-за неточности расчёта")
        row.addWidget(self.sp_margin)
        row.addStretch(1)
        lay.addLayout(row)

        calib = QGroupBox("Калибровка (один раз для шрифта и размера в программе плоттера)")
        form = QFormLayout(calib)
        self.ed_calib = QLineEdit()
        form.addRow("Эталонная строка:", self.ed_calib)
        self.sp_calib = _spin(0, 5000, 0.5, 1, " мм")
        self.sp_calib.setSpecialValueText("не измерена")
        self.sp_calib.setToolTip("Напишите эталонную строку в программе плоттера тем же шрифтом\n"
                                 "и размером и измерьте её длину от первой до последней буквы")
        form.addRow("Её длина на бумаге:", self.sp_calib)
        adv = QHBoxLayout()
        adv.addWidget(QLabel("межбуквенный интервал"))
        self.sp_gap = _spin(0, 500, 1, 0, " ед.")
        adv.addWidget(self.sp_gap)
        adv.addWidget(QLabel("пробел"))
        self.sp_space = _spin(0, 1000, 1, 0, " ед.")
        adv.addWidget(self.sp_space)
        adv.addStretch(1)
        form.addRow("Ширины:", adv)
        self.lbl_scale = QLabel("")
        form.addRow("", self.lbl_scale)
        lay.addWidget(calib)

        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Исходный текст:"))
        self.ed_in = QPlainTextEdit()
        self.ed_in.setPlaceholderText("Вставьте текст сюда")
        ll.addWidget(self.ed_in)
        split.addWidget(left)

        self.tabs = QTabWidget()
        self.ed_out = QPlainTextEdit()
        self.ed_out.setReadOnly(True)
        self.tabs.addTab(self.ed_out, "Текст для программы плоттера")
        self.preview = Preview()
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.preview)
        self.scroll.setWidgetResizable(False)
        self.tabs.addTab(self.scroll, "Предпросмотр")
        self.tabs.currentChanged.connect(lambda _i: self._update_preview())
        split.addWidget(self.tabs)
        split.setSizes([500, 700])
        lay.addWidget(split, 1)

        bottom = QHBoxLayout()
        self.btn_copy = QPushButton("Копировать результат")
        self.btn_copy.clicked.connect(self.copy_result)
        bottom.addWidget(self.btn_copy)
        btn_save = QPushButton("Сохранить в файл…")
        btn_save.clicked.connect(self.save_result)
        bottom.addWidget(btn_save)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        bottom.addWidget(self.status, 1)
        lay.addLayout(bottom)

        self.setCentralWidget(root)

        for w in (self.sp_line, self.sp_margin, self.sp_calib, self.sp_gap, self.sp_space):
            w.valueChanged.connect(self._changed)
        self.cb_hyph.toggled.connect(self._changed)
        self.ed_calib.textChanged.connect(self._changed)
        self.ed_in.textChanged.connect(self._timer.start)

    def _load_values(self):
        s = self.s
        self._loading = True        # сигналы полей не должны затирать ещё не выставленные значения
        self.cb_hyph.setChecked(s.hyphenate)
        self.sp_line.setValue(s.line_mm)
        self.sp_margin.setValue(s.margin_pct)
        self.ed_calib.setText(s.calib_text)
        self.sp_calib.setValue(s.calib_mm)
        self.sp_gap.setValue(s.gap)
        self.sp_space.setValue(s.space)
        if not self.ed_in.toPlainText():
            self.ed_in.setPlainText(SAMPLE)
        self._loading = False

    def _changed(self, *_):
        if self._loading:
            return
        s = self.s
        s.hyphenate = self.cb_hyph.isChecked()
        s.line_mm = self.sp_line.value()
        s.margin_pct = self.sp_margin.value()
        s.calib_text = self.ed_calib.text()
        s.calib_mm = self.sp_calib.value()
        s.gap = self.sp_gap.value()
        s.space = self.sp_space.value()
        if self.metrics is not None:
            self.metrics.gap, self.metrics.space = s.gap, s.space
        self._save()
        self._timer.start()

    def _save(self):
        if self.persist:
            save_settings(self.s)

    # ------------------------------------------------------------ actions
    def choose_font(self):
        start = str(Path(self.s.font_path).parent) if self.s.font_path else ""
        path, _ = QFileDialog.getOpenFileName(self, "Шрифт плоттера", start, "Шрифты (*.gfont)")
        if path:
            self.load_font(path)
            self.recompute()

    def load_font(self, path: str, quiet: bool = False) -> bool:
        try:
            glyphs = read_gfont(path)
        except GFontError as exc:
            if not quiet:
                QMessageBox.warning(self, "Шрифт", str(exc))
            return False
        self.glyphs = glyphs
        self.metrics = Metrics.from_glyphs(glyphs, gap=self.s.gap, space=self.s.space)
        self.s.font_path = path
        self.font_edit.setText(path)
        hy = "есть" if self.metrics.has("-") else "НЕТ — переносы с дефисом отключены"
        self.font_info.setText(f"{len(glyphs)} символов, дефис: {hy}")
        self._save()
        return True

    def recompute(self):
        if self.metrics is None:
            self.status.setText("Откройте шрифт .gfont, которым пишет плоттер.")
            self.ed_out.setPlainText("")
            self.result = None
            return
        s, m = self.s, self.metrics
        m.missing.clear()
        k, calibrated = s.mm_per_unit(m)
        limit = s.max_units(m)
        if calibrated:
            self.lbl_scale.setText(f"1 мм = {1 / k:.1f} ед. шрифта; в строку помещается "
                                   f"{limit:.0f} ед. (с запасом {s.margin_pct:g} %)")
        else:
            self.lbl_scale.setText("Не откалибровано — ширина строки примерная. Измерьте эталонную "
                                   "строку на бумаге и введите её длину.")
        hyph = s.hyphenate and m.has("-")
        self.result = wrap_text(self.ed_in.toPlainText(), m.text_width, limit, hyphenate=hyph)
        self.ed_out.setPlainText(self.result.text)
        self._update_preview()
        msg = [f"Строк: {len(self.result.lines)}",
               f"переносов: {self.result.hyphens}" if hyph else "переносы выключены"]
        if self.result.overflow:
            nums = ", ".join(str(i + 1) for i in self.result.overflow[:10])
            msg.append(f"не помещаются целиком (длинное слово): строки {nums}")
        missing = m.missing_in(self.result.lines)
        if missing:
            msg.append("нет в шрифте: " + " ".join(missing[:20]))
        self.status.setText("; ".join(msg))

    def _update_preview(self):
        if self.result is None or self.metrics is None:
            return
        k, _ = self.s.mm_per_unit(self.metrics)
        avail = self.scroll.viewport().width() - self.scroll.verticalScrollBar().sizeHint().width()
        self.preview.set_data(self.result.lines, self.glyphs, self.metrics,
                              self.s.max_units(self.metrics), self.s.line_mm / k, avail)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._update_preview()

    def copy_result(self):
        if self.result is not None:
            QGuiApplication.clipboard().setText(self.result.text)
            self.status.setText("Результат скопирован. Вставьте его в программу плоттера.")

    def save_result(self):
        if self.result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить текст", "текст_с_переносами.txt",
                                              "Текст (*.txt)")
        if path:
            try:
                Path(path).write_text(self.result.text, encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "Сохранение", f"Не удалось сохранить: {exc}")


def main(argv=None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    w = MainWindow()
    w.show()
    return app.exec()
