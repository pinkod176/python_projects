"""Окно «Нарисовать свой почерк».

Слева — символы по группам (миниатюры, статус, прогресс), в центре — холст и панели
инструментов, справа — предпросмотр. Внизу — проект, экспорт, заполнение недостающих.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PySide6.QtCore import QByteArray, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton,
                               QSlider, QSpinBox, QSplitter, QToolButton, QVBoxLayout, QWidget)

from gfont import __version__
from gfont.errors import UserError
from gfont.session import resource_dir

from ..settings import AppSettings, settings_dir
from ..workers import TaskWorker
from .canvas import DrawCanvas
from .charsets import ALL_CODES, label
from .dialogs import CandidatesDialog, ExportDialog, FillModeDialog
from .export import ExportOptions, ExportResult, export_project, import_gfont
from .fill import apply_candidates, font_candidates, similar_candidates
from .glyph_list import GlyphBrowser
from .preview import PreviewPanel
from .project import DRAWN, MAX_VARIANTS, SKIPPED, Project
from .strokes import glyph_to_gfont, ratio_warning
from .template import TemplateProvider
from .theme import apply_theme

FONT_FILTER = "Шрифты (*.ttf *.otf *.ttc *.otc *.woff *.woff2)"
AUTOSAVE_MS = 30_000
BIG = "QPushButton { padding: 6px 12px; min-height: 26px; }"


def drafts_dir() -> Path:
    return settings_dir() / "drafts"


def draft_path() -> Path:
    return drafts_dir() / "автосохранение.gfproj"


class LabeledSlider(QWidget):
    changed = Signal(int)

    def __init__(self, title: str, lo: int, hi: int, value: int, fmt: str = "{} %", tip: str = ""):
        super().__init__()
        self.fmt = fmt
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(title))
        self.s = QSlider(Qt.Horizontal)
        self.s.setRange(lo, hi)
        self.s.setValue(value)
        self.s.setMinimumWidth(90)
        self.s.setFocusPolicy(Qt.NoFocus)        # стрелки — для перехода по символам
        self.lbl = QLabel(fmt.format(value))
        self.lbl.setMinimumWidth(44)
        lay.addWidget(self.s, 1)
        lay.addWidget(self.lbl)
        if tip:
            self.setToolTip(tip)
        self.s.valueChanged.connect(self._on)

    def _on(self, v: int) -> None:
        self.lbl.setText(self.fmt.format(v))
        self.changed.emit(v)

    def value(self) -> int:
        return self.s.value()

    def set_value(self, v: int) -> None:
        self.s.blockSignals(True)
        self.s.setValue(int(v))
        self.s.blockSignals(False)
        self.lbl.setText(self.fmt.format(self.s.value()))


class DrawWindow(QMainWindow):
    def __init__(self, settings: Optional[AppSettings] = None, parent=None, *, restore_draft: bool = True):
        super().__init__(parent)
        self.settings = settings or AppSettings()
        self.project = Project()
        self.provider = TemplateProvider()
        self.task: Optional[TaskWorker] = None
        self.last_export: Optional[ExportResult] = None
        self._gcache: Dict[int, list] = {}
        self._autosave_dirty = False
        icon = resource_dir() / "icon.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self._build_ui()
        self._build_menu()
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(120)
        self.preview_timer.timeout.connect(self._refresh_preview)
        self.autosave = QTimer(self)
        self.autosave.setInterval(AUTOSAVE_MS)
        self.autosave.timeout.connect(self.autosave_now)
        self.autosave.start()
        self._restore_window()
        self.set_dark(bool(self.settings["dark_theme"]))
        self._load_project(Project(), quiet=True)
        if restore_draft:
            QTimer.singleShot(0, self._offer_draft)

    # ================================================================ UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 6)
        split = QSplitter(Qt.Horizontal)

        self.browser = GlyphBrowser()
        self.browser.codeSelected.connect(self.go_to)
        split.addWidget(self.browser)

        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        self.canvas = DrawCanvas(self.provider)
        self.canvas.strokesChanged.connect(self._on_strokes_changed)
        ml.addWidget(self.canvas, 1)
        ml.addWidget(self._build_tools())
        split.addWidget(mid)

        self.preview = PreviewPanel()
        self.preview.textChanged.connect(self._on_text)
        self.preview.penChanged.connect(self._on_pen)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([330, 700, 400])
        self.split = split
        root.addWidget(split, 1)

        bottom = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить проект")
        self.btn_save.clicked.connect(self.save_project)
        self.btn_open = QPushButton("Открыть проект…")
        self.btn_open.clicked.connect(self.open_project_dialog)
        self.btn_export = QPushButton("Экспорт в .gfont…")
        self.btn_export.setStyleSheet("QPushButton { font-weight: bold; padding: 6px 14px; min-height: 26px; }")
        self.btn_export.clicked.connect(self.export_dialog)
        self.btn_fill = QPushButton("Заполнить недостающие символы…")
        self.btn_fill.clicked.connect(self.fill_dialog)
        for b in (self.btn_save, self.btn_open, self.btn_fill):
            b.setStyleSheet(BIG)
        self.progress = QProgressBar()
        self.progress.setFormat("")
        self.progress.setValue(0)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_task)
        for w in (self.btn_save, self.btn_open, self.btn_export, self.btn_fill):
            bottom.addWidget(w)
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.btn_cancel)
        root.addLayout(bottom)
        self.setCentralWidget(central)
        self.lbl_warn = QLabel("")
        self.lbl_warn.setStyleSheet("color: #c77700;")
        self.statusBar().addPermanentWidget(self.lbl_warn)

    def _tool_button(self, text: str, tip: str, slot) -> QPushButton:
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setStyleSheet(BIG)
        b.setFocusPolicy(Qt.NoFocus)
        b.clicked.connect(slot)
        return b

    def _build_tools(self) -> QWidget:
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        v = QVBoxLayout(box)
        v.setContentsMargins(6, 4, 6, 4)
        v.setSpacing(4)

        r1 = QHBoxLayout()
        self.b_undo = self._tool_button("↶ Отменить", "Отменить штрих (Ctrl+Z)", self.canvas.undo)
        self.b_redo = self._tool_button("↷ Повторить", "Повторить (Ctrl+Y)", self.canvas.redo)
        self.b_last = self._tool_button("Удалить последний штрих", "Backspace", self.canvas.delete_last)
        self.b_clear = self._tool_button("Очистить символ", "Удалить все штрихи символа",
                                         self.canvas.clear_glyph)
        for b in (self.b_undo, self.b_redo, self.b_last, self.b_clear):
            r1.addWidget(b)
        r1.addSpacing(10)
        self.sl_smooth = LabeledSlider("Сглаживание", 0, 100, 40, tip="0 % — без сглаживания (острые углы "
                                       "и мелкие изгибы сохраняются), 100 % — максимально плавно")
        self.sl_smooth.changed.connect(self._on_smooth)
        r1.addWidget(self.sl_smooth, 1)
        self.sl_density = LabeledSlider("Плотность точек", 50, 200, 100, tip="Шаг точек = 25 ед. / плотность "
                                        "(в эталоне шаг около 27)")
        self.sl_density.changed.connect(self._on_density)
        r1.addWidget(self.sl_density, 1)
        v.addLayout(r1)

        r2 = QHBoxLayout()
        self.b_prev = self._tool_button("◀ Предыдущий", "Стрелка влево", self.prev_glyph)
        self.b_skip = self._tool_button("Пропустить", "Отметить символ пропущенным и перейти дальше",
                                        self.skip_glyph)
        self.b_next = self._tool_button("Следующий ▶", "Enter или стрелка вправо", self.next_glyph)
        for b in (self.b_prev, self.b_skip, self.b_next):
            r2.addWidget(b)
        r2.addSpacing(10)
        self.ch_align = QCheckBox("Автовыравнивание по базовой линии")
        self.ch_align.setToolTip("Слегка подтянуть низ буквы к базовой линии (кроме букв с нижними "
                                 "выносными: р, у, д, ц, щ …)")
        self.ch_align.setFocusPolicy(Qt.NoFocus)
        self.ch_align.toggled.connect(self._on_align)
        r2.addWidget(self.ch_align)
        r2.addStretch(1)
        self.rb_draw = QRadioButton("Рисовать")
        self.rb_edit = QRadioButton("Правка точек")
        self.rb_edit.setToolTip("Перетаскивайте точки штрихов; правая кнопка мыши — удалить штрих")
        g = QButtonGroup(self)
        g.addButton(self.rb_draw)
        g.addButton(self.rb_edit)
        self.rb_draw.setChecked(True)
        for rb in (self.rb_draw, self.rb_edit):
            rb.setFocusPolicy(Qt.NoFocus)
            rb.toggled.connect(self._on_tool)
            r2.addWidget(rb)
        r2.addSpacing(10)
        r2.addWidget(QLabel("Вариант:"))
        self.sp_var = QSpinBox()
        self.sp_var.setRange(1, MAX_VARIANTS)
        self.sp_var.setToolTip("Несколько попыток одного символа (2–5). При экспорте можно разложить "
                               "по альтернативным записям")
        self.sp_var.valueChanged.connect(self._on_variant)
        r2.addWidget(self.sp_var)
        v.addLayout(r2)

        r3 = QHBoxLayout()
        self.ch_tpl = QCheckBox("Шаблон (T)")
        self.ch_tpl.setChecked(True)
        self.ch_tpl.setFocusPolicy(Qt.NoFocus)
        self.ch_tpl.toggled.connect(self._on_view)
        r3.addWidget(self.ch_tpl)
        self.sl_opacity = LabeledSlider("Видимость", 5, 100, 35, tip="Насколько заметен пунктирный шаблон")
        self.sl_opacity.changed.connect(self._on_view)
        r3.addWidget(self.sl_opacity, 1)
        self.sl_size = LabeledSlider("Размер шаблона", 80, 120, 100, tip="Крупнее или мельче рисовать "
                                     "(±20 %). Меняет разметку холста вместе с шаблоном; итоговый размер "
                                     "букв в файле от этого не меняется")
        self.sl_size.changed.connect(self._on_size)
        r3.addWidget(self.sl_size, 1)
        self.ch_order = QCheckBox("Порядок и направление штрихов")
        self.ch_order.setToolTip("Осевая линия образца с номерами и стрелками (рекомендуемый порядок письма)")
        self.ch_order.setFocusPolicy(Qt.NoFocus)
        self.ch_order.toggled.connect(self._on_view)
        r3.addWidget(self.ch_order)
        self.ch_guides = QCheckBox("Линии")
        self.ch_guides.setChecked(True)
        self.ch_guides.setToolTip("Линии тетради: базовая (красная), строчных (синяя), заглавных (серая), "
                                  "выносных (пунктир)")
        self.ch_guides.setFocusPolicy(Qt.NoFocus)
        self.ch_guides.toggled.connect(self._on_view)
        r3.addWidget(self.ch_guides)
        self.b_sample = QToolButton()
        self.b_sample.setText("Образец…")
        self.b_sample.setToolTip("Шрифт-образец шаблона (TTF/OTF) или свой шаблон .gfont")
        self.b_sample.setFocusPolicy(Qt.NoFocus)
        self.b_sample.clicked.connect(self.choose_sample)
        r3.addWidget(self.b_sample)
        v.addLayout(r3)
        return box

    def _build_menu(self) -> None:
        def act(menu, text, slot, shortcut=None, checkable=False):
            a = QAction(text, self)
            if shortcut:
                a.setShortcuts(shortcut if isinstance(shortcut, list) else [QKeySequence(shortcut)])
            a.setCheckable(checkable)
            a.triggered.connect(slot)
            menu.addAction(a)
            return a

        m = self.menuBar().addMenu("&Проект")
        act(m, "Новый проект", self.new_project)
        act(m, "Открыть проект…", self.open_project_dialog, QKeySequence.Open)
        act(m, "Сохранить проект", self.save_project, QKeySequence.Save)
        act(m, "Сохранить проект как…", self.save_project_as, "Ctrl+Shift+S")
        m.addSeparator()
        act(m, "Открыть существующий .gfont в редакторе…", self.open_gfont_dialog)
        act(m, "Экспорт в .gfont…", self.export_dialog, "Ctrl+E")
        m.addSeparator()
        act(m, "Закрыть окно", self.close, "Ctrl+W")

        s = self.menuBar().addMenu("&Символ")
        act(s, "Отменить штрих", self.canvas.undo, QKeySequence.Undo)
        act(s, "Повторить", self.canvas.redo, [QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        act(s, "Удалить последний штрих", self.canvas.delete_last, "Backspace")
        act(s, "Очистить символ", self.canvas.clear_glyph)
        s.addSeparator()
        act(s, "Следующий символ", self.next_glyph,
            [QKeySequence(Qt.Key_Return), QKeySequence(Qt.Key_Enter), QKeySequence(Qt.Key_Right)])
        act(s, "Предыдущий символ", self.prev_glyph, [QKeySequence(Qt.Key_Left)])
        act(s, "Пропустить", self.skip_glyph)

        t = self.menuBar().addMenu("&Шаблон")
        self.a_tpl = act(t, "Показывать шаблон", lambda on: self.ch_tpl.setChecked(on), "T", True)
        act(t, "Шрифт-образец или свой шаблон (TTF/OTF/.gfont)…", self.choose_sample)
        act(t, "Встроенный образец (DejaVu Sans)", self.default_sample)
        t.addSeparator()
        act(t, "Заполнить недостающие символы…", self.fill_dialog)
        act(t, "Использовать образцы шрифта как заготовку…", self.seed_from_font)

        v = self.menuBar().addMenu("&Вид")
        self.a_dark = act(v, "Тёмная тема", self.set_dark, None, True)
        act(v, "Вписать холст в окно", self.canvas.fit, "Ctrl+0")
        act(v, "Крупнее", lambda: self.canvas.zoom_by(1.2), "Ctrl+=")
        act(v, "Мельче", lambda: self.canvas.zoom_by(1 / 1.2), "Ctrl+-")

    # ================================================================ проект
    def _load_project(self, project: Project, quiet: bool = False) -> None:
        self.project = project
        st = project.settings
        self.canvas.set_project(project)
        self._gcache.clear()
        self.sl_smooth.set_value(int(round(st.smoothing * 100)))
        self.sl_density.set_value(int(round(st.density * 100)))
        self.sl_size.set_value(int(round(st.size * 100)))
        self.sl_opacity.set_value(int(round(st.template_opacity * 100)))
        for w, val in ((self.ch_align, st.autoalign), (self.ch_tpl, st.show_template),
                       (self.ch_order, st.show_order), (self.ch_guides, st.show_guides)):
            w.blockSignals(True)
            w.setChecked(val)
            w.blockSignals(False)
        self.a_tpl.setChecked(st.show_template)
        self.preview.set_pen(st.pen)
        self.preview.ed.blockSignals(True)
        self.preview.ed.setText(st.preview_text)
        self.preview.ed.blockSignals(False)
        try:
            if st.hint_gfont and Path(st.hint_gfont).is_file():
                self.provider.set_gfont(st.hint_gfont)
            else:
                self.provider.set_font(st.sample_font or None)
        except UserError as exc:
            self.provider.set_font(None)
            self.statusBar().showMessage(str(exc), 8000)
        self.browser.set_source(project, self.gfont_of)
        first = next((c for c in ALL_CODES if project.status(c) not in (DRAWN, SKIPPED)), ALL_CODES[0])
        self.go_to(first)
        self._update_title()
        self._update_warning()

    def _update_title(self) -> None:
        name = self.project.path.name if self.project.path else self.project.name
        self.setWindowTitle(f"GfontConverter {__version__} — Нарисовать свой почерк — {name}"
                            + (" *" if self.project.dirty else ""))

    def _ask_save_changes(self) -> bool:
        """True — можно продолжать (сохранено или изменения не нужны)."""
        if not self.project.dirty or os.environ.get("GFONT_NO_DIALOGS"):
            return True
        r = QMessageBox.question(self, "Несохранённые изменения", "Сохранить проект?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Cancel:
            return False
        if r == QMessageBox.Save:
            return self.save_project()
        return True

    def new_project(self) -> None:
        if self._ask_save_changes():
            self._load_project(Project())

    def _default_dir(self) -> str:
        return self.settings["draw_last_dir"] or str(Path.home())

    def open_project_dialog(self) -> None:
        if not self._ask_save_changes():
            return
        p, _ = QFileDialog.getOpenFileName(self, "Открыть проект", self._default_dir(),
                                           "Проект почерка (*.gfproj)")
        if p:
            self.open_project(p)

    def open_project(self, path) -> bool:
        try:
            pr = Project.load(path)
        except UserError as exc:
            self.show_error(str(exc))
            return False
        self.settings["draw_last_dir"] = str(Path(path).parent)
        self._load_project(pr)
        self.statusBar().showMessage(f"Открыт проект {Path(path).name}", 5000)
        return True

    def save_project(self) -> bool:
        if self.project.path is None:
            return self.save_project_as()
        return self._save_to(self.project.path)

    def save_project_as(self) -> bool:
        start = str(Path(self._default_dir()) / f"{self.project.name}.gfproj")
        p, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", start, "Проект почерка (*.gfproj)")
        if not p:
            return False
        if not p.lower().endswith(".gfproj"):
            p += ".gfproj"
        return self._save_to(Path(p))

    def _save_to(self, path: Path) -> bool:
        self._sync_settings()
        try:
            self.project.save(path)
        except UserError as exc:
            self.show_error(str(exc))
            return False
        self.project.path = Path(path)
        self.project.dirty = False
        self.settings["draw_last_dir"] = str(Path(path).parent)
        self.settings["draw_last_project"] = str(path)
        self._remove_draft()
        self._update_title()
        self.statusBar().showMessage(f"Проект сохранён: {path}", 5000)
        return True

    def _sync_settings(self) -> None:
        st = self.project.settings
        st.preview_text = self.preview.ed.text()
        st.pen = self.preview.pen()

    # ---- автосохранение и восстановление ----
    def autosave_now(self) -> None:
        if not self._autosave_dirty:
            return
        self._sync_settings()
        try:
            d = self.project.to_dict()
            d["draft_of"] = str(self.project.path or "")
            drafts_dir().mkdir(parents=True, exist_ok=True)
            tmp = draft_path().with_suffix(".tmp")
            tmp.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            os.replace(tmp, draft_path())
            self._autosave_dirty = False
        except OSError:
            pass   # автосохранение не должно мешать работе

    def _remove_draft(self) -> None:
        self._autosave_dirty = False
        try:
            draft_path().unlink()
        except OSError:
            pass

    def _offer_draft(self) -> None:
        p = draft_path()
        if not p.is_file() or os.environ.get("GFONT_NO_DIALOGS"):
            return
        from datetime import datetime
        when = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
        r = QMessageBox.question(self, "Восстановить черновик?",
                                 f"Найден несохранённый черновик от {when} (программа закрылась, не "
                                 "сохранив проект). Восстановить его?",
                                 QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes:
            self._remove_draft()
            return
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            pr = Project.from_dict(d)
            if d.get("draft_of"):
                pr.path = Path(d["draft_of"])
            pr.dirty = True
        except (OSError, ValueError, UserError) as exc:
            self.show_error(f"Черновик не читается: {exc}")
            return
        self._load_project(pr)
        self._autosave_dirty = True

    # ================================================================ навигация
    def go_to(self, code: int) -> None:
        self.canvas.set_code(code, 0)
        self.sp_var.blockSignals(True)
        self.sp_var.setValue(1)
        self.sp_var.blockSignals(False)
        self.browser.select(code)
        self._update_glyph_preview()
        self.canvas.setFocus()
        e = self.project.glyphs.get(code)
        info = f"{label(code)}  U+{code:04X}"
        if e and e.status == DRAWN and e.source in ("font", "similar"):
            info += " — заполнен автоматически; можно очистить и нарисовать заново"
        self.statusBar().showMessage(info)

    def _step(self, d: int) -> None:
        codes = ALL_CODES
        i = codes.index(self.canvas.code) if self.canvas.code in codes else 0
        j = min(len(codes) - 1, max(0, i + d))
        if j != i:
            self.go_to(codes[j])

    def next_glyph(self) -> None:
        self._step(1)

    def prev_glyph(self) -> None:
        self._step(-1)

    def skip_glyph(self) -> None:
        e = self.project.entry(self.canvas.code)
        if e.status != DRAWN:
            e.status = SKIPPED
            self.project.dirty = True
            self._autosave_dirty = True
            self.browser.refresh(self.canvas.code)
            self._update_title()
        self.next_glyph()

    # ================================================================ изменения
    def gfont_of(self, code: int) -> Optional[list]:
        """Основной вариант символа в координатах .gfont (как в файле), с кэшем."""
        if code in self._gcache:
            return self._gcache[code]
        e = self.project.glyphs.get(code)
        if e is None or not e.has_drawing():
            return None
        st = self.project.settings
        g = glyph_to_gfont(e.strokes, self.project.geometry(), code=code, smoothing=st.smoothing,
                           density=st.density, autoalign=st.autoalign)
        self._gcache[code] = g
        return g

    def _invalidate_all(self) -> None:
        self._gcache.clear()
        self.canvas.invalidate()
        self.browser.refresh_all()
        self._update_glyph_preview()
        self.preview_timer.start()
        self._update_warning()

    def _on_strokes_changed(self, code: int) -> None:
        self._gcache.pop(code, None)
        self._autosave_dirty = True
        self.browser.refresh(code)
        self._update_glyph_preview()
        self.preview_timer.start()
        self._update_warning()
        self._update_title()

    def _update_glyph_preview(self) -> None:
        code = self.canvas.code
        if self.canvas.variant == 0:
            g = self.gfont_of(code)
        else:
            st = self.project.settings
            g = glyph_to_gfont(self.canvas.strokes(), self.project.geometry(), code=code,
                               smoothing=st.smoothing, density=st.density, autoalign=st.autoalign)
        self.preview.glyph.set_glyph(g, self.preview.pen())

    def _on_text(self, _t: str) -> None:
        self.project.settings.preview_text = self.preview.ed.text()
        self.preview_timer.start()

    def _on_pen(self, v: float) -> None:
        self.project.settings.pen = v
        self.canvas.update()

    def _refresh_preview(self) -> None:
        text = self.preview.ed.text()
        glyphs = {ch: self.gfont_of(ord(ch)) for ch in dict.fromkeys(text) if not ch.isspace()}
        self.preview.set_line(text, glyphs)

    def _update_warning(self) -> None:
        tm = self.project.geometry().tm
        drawn = {}
        for c, e in self.project.glyphs.items():
            if e.has_drawing() and e.source in ("", "user"):
                g = self.gfont_of(c)
                if g:
                    drawn[c] = [np.asarray(s, dtype=float) for s in g if len(s) >= 2]
        self.lbl_warn.setText(("⚠ " + w) if (w := ratio_warning(drawn, tm)) else "")

    def _settings_changed(self) -> None:
        self.project.dirty = True
        self._autosave_dirty = True
        self._update_title()

    def _on_smooth(self, v: int) -> None:
        self.project.settings.smoothing = v / 100.0
        self._settings_changed()
        self._invalidate_all()

    def _on_density(self, v: int) -> None:
        self.project.settings.density = v / 100.0
        self._settings_changed()
        self._invalidate_all()

    def _on_align(self, on: bool) -> None:
        self.project.settings.autoalign = on
        self._settings_changed()
        self._invalidate_all()

    def _on_size(self, v: int) -> None:
        self.project.set_size(v / 100.0)
        self._settings_changed()
        if self.canvas._auto_fit:
            self.canvas.fit()
        self._invalidate_all()

    def _on_view(self, *_a) -> None:
        st = self.project.settings
        st.show_template = self.ch_tpl.isChecked()
        st.template_opacity = self.sl_opacity.value() / 100.0
        st.show_order = self.ch_order.isChecked()
        st.show_guides = self.ch_guides.isChecked()
        self.a_tpl.blockSignals(True)
        self.a_tpl.setChecked(st.show_template)
        self.a_tpl.blockSignals(False)
        self._autosave_dirty = True
        self.canvas.update()

    def _on_tool(self, *_a) -> None:
        self.canvas.tool = "edit" if self.rb_edit.isChecked() else "draw"
        self.canvas.setCursor(Qt.PointingHandCursor if self.canvas.tool == "edit" else Qt.CrossCursor)
        self.canvas.update()

    def _on_variant(self, v: int) -> None:
        self.canvas.set_code(self.canvas.code, v - 1)
        self._update_glyph_preview()
        self.canvas.setFocus()

    # ================================================================ шаблон
    def choose_sample(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Шрифт-образец или свой шаблон", self._default_dir(),
                                           FONT_FILTER[:-1] + " *.gfont);;Шаблон .gfont (*.gfont)")
        if not p:
            return
        st = self.project.settings
        try:
            if p.lower().endswith(".gfont"):
                self.provider.set_gfont(p)
                st.hint_gfont, st.sample_font = p, ""
            else:
                self.provider.set_font(p)
                if self.provider.error:
                    self.show_error(self.provider.error + "\nОставлен встроенный образец.")
                    return
                st.sample_font, st.hint_gfont = p, ""
        except UserError as exc:
            self.show_error(str(exc))
            return
        self._settings_changed()
        self.statusBar().showMessage(f"Образец шаблона: {self.provider.source_name}", 5000)
        self.canvas.update()

    def default_sample(self) -> None:
        self.provider.set_font(None)
        st = self.project.settings
        st.sample_font = st.hint_gfont = ""
        self._settings_changed()
        self.canvas.update()

    # ================================================================ импорт .gfont
    def open_gfont_dialog(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Открыть .gfont в редакторе", self._default_dir(),
                                           "Файл .gfont (*.gfont)")
        if p:
            self.open_gfont(p)

    def open_gfont(self, path: str) -> List[int]:
        if self.project.counts()[0] and not os.environ.get("GFONT_NO_DIALOGS"):
            r = QMessageBox.question(self, "Открыть .gfont",
                                     "Символы из файла заменят такие же символы проекта. Продолжить?")
            if r != QMessageBox.Yes:
                return []
        try:
            got = import_gfont(path, self.project)
        except UserError as exc:
            self.show_error(str(exc))
            return []
        st = self.project.settings
        st.template = str(path)          # экспорт — поверх этого же файла
        st.remove_old = False
        self._settings_changed()
        self._invalidate_all()
        self.go_to(self.canvas.code)
        self.statusBar().showMessage(f"Из «{Path(path).name}» загружено символов: {len(got)}. "
                                     "Экспорт будет собран поверх этого файла.", 8000)
        return got

    # ================================================================ заполнение
    def missing_codes(self) -> List[int]:
        return [c for c in ALL_CODES if not (self.project.glyphs.get(c) and self.project.glyphs[c].has_drawing())]

    def fill_dialog(self) -> None:
        missing = self.missing_codes()
        if not missing:
            QMessageBox.information(self, "Заполнение", "Все символы уже нарисованы.")
            return
        d = FillModeDialog(len(missing), self)
        if d.exec() != FillModeDialog.Accepted or d.choice in (None, "none"):
            return
        if d.choice == "similar":
            cands = similar_candidates(self.project, missing)
            if not cands:
                QMessageBox.information(self, "Заполнение", "Похожих нарисованных символов нет. Нарисуйте, "
                                        "например, «-», «е», «и», «N», «o» — из них получатся ‑ – —, ё, й, №.")
                return
            self._review(cands, "Повторить из похожих")
        else:
            p, _ = QFileDialog.getOpenFileName(self, "Шрифт для недостающих символов", self._default_dir(),
                                               FONT_FILTER)
            if p:
                self._fill_from_font(p, missing, fit=True, title="Из шрифта")

    def seed_from_font(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Шрифт-заготовка", self._default_dir(), FONT_FILTER)
        if p:
            self._fill_from_font(p, self.missing_codes(), fit=False, title="Образцы шрифта как заготовка")

    def _fill_from_font(self, font: str, codes: List[int], fit: bool, title: str) -> Optional[TaskWorker]:
        project = self.project

        def job(progress, cancel, log):
            return font_candidates(font, codes, project, fit_to_user=fit,
                                   progress=lambda d, t: progress(d, t, "Символы"), cancel=cancel)

        return self.run_task(job, f"{title}: {Path(font).name}", lambda c: self._review(c, title))

    def _review(self, cands, title: str) -> None:
        if not cands:
            QMessageBox.information(self, title, "Подходящих символов не нашлось.")
            return
        dlg = CandidatesDialog(self.project, cands, title, self, dark=self.a_dark.isChecked())
        if os.environ.get("GFONT_NO_DIALOGS"):
            sel = cands
        elif dlg.exec() == CandidatesDialog.Accepted:
            sel = dlg.selected()
        else:
            return
        apply_candidates(self.project, sel)
        self._autosave_dirty = True
        for c in sel:
            self._gcache.pop(c, None)
        self._invalidate_all()
        self._update_title()
        self.statusBar().showMessage(f"Заполнено символов: {len(sel)}", 5000)

    # ================================================================ экспорт
    def _default_export(self) -> Path:
        folder = Path(self.settings["last_save_dir"] or self._default_dir())
        base = (self.project.path.stem if self.project.path else self.project.name) or "почерк"
        return folder / f"{base}.gfont"

    def export_dialog(self) -> None:
        missing = self.missing_codes()
        if missing and not os.environ.get("GFONT_NO_DIALOGS"):
            box = QMessageBox(QMessageBox.Warning, "Не все символы нарисованы",
                              f"Не нарисовано символов: {len(missing)} "
                              f"({''.join(chr(c) for c in missing[:40])}{'…' if len(missing) > 40 else ''}).\n"
                              "Без них в файле этих символов не будет (или останутся из шаблона, если "
                              "не убирать старые буквы).", parent=self)
            b_fill = box.addButton("Заполнить…", QMessageBox.AcceptRole)
            b_go = box.addButton("Экспортировать как есть", QMessageBox.DestructiveRole)
            box.addButton("Отмена", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is b_fill:
                self.fill_dialog()
                return
            if box.clickedButton() is not b_go:
                return
        d = ExportDialog(self.project, self._default_export(), self)
        if d.exec() != ExportDialog.Accepted:
            return
        self.start_export(d.options())

    def start_export(self, opts: ExportOptions) -> Optional[TaskWorker]:
        """Экспорт в фоне (без диалогов — используется и в смоук-тесте)."""
        if not any(e.has_drawing() for e in self.project.glyphs.values()):
            self.show_error("Нарисуйте хотя бы один символ.")
            return None
        st = self.project.settings
        st.template, st.remove_old, st.normalize = opts.template, opts.remove_old, opts.normalize
        st.alt_mode, st.seed = opts.alt_mode, opts.seed
        self.settings["last_save_dir"] = str(Path(opts.output).parent)
        self._sync_settings()
        snapshot = Project.from_dict(self.project.to_dict())

        def job(progress, cancel, log):
            return export_project(snapshot, opts, progress=lambda d, t: progress(d, t, "Глифы"),
                                  cancel=cancel)

        return self.run_task(job, f"Экспорт {Path(opts.output).name}", self._on_exported)

    def _on_exported(self, res: ExportResult) -> None:
        self.last_export = res
        ok = res.report.validation is not None and res.report.validation.ok
        self.statusBar().showMessage(("Готово: " if ok else "ОШИБКА проверки: ") + res.output, 10000)
        if os.environ.get("GFONT_NO_DIALOGS"):
            return
        box = QMessageBox(QMessageBox.Information if ok else QMessageBox.Warning, "Экспорт в .gfont",
                          ("Файл сохранён и проверен.\n\n" if ok else "Файл сохранён, но проверка нашла ошибки.\n\n")
                          + f"Нарисовано вами: {len(res.by_user)}\n"
                          f"Заполнено автоматически: {len(res.auto)}\n"
                          f"Нет: {len(res.missing)}\n\n{res.output}", parent=self)
        box.setDetailedText(res.text())
        box.exec()

    # ================================================================ фоновые задачи
    def run_task(self, fn, title: str, on_done) -> Optional[TaskWorker]:
        if self.task is not None and self.task.isRunning():
            self.show_error("Уже выполняется другая операция.")
            return None
        t = TaskWorker(fn, title)
        t.progress.connect(self._on_progress)
        t.succeeded.connect(on_done)
        t.failed.connect(self.show_error)
        t.cancelled.connect(lambda: self.statusBar().showMessage("Отменено", 5000))
        t.finished.connect(lambda: self._busy(False))
        self.task = t
        self._busy(True, title)
        t.start()
        return t

    def _busy(self, on: bool, title: str = "") -> None:
        for w in (self.btn_export, self.btn_fill, self.btn_open):
            w.setEnabled(not on)
        self.btn_cancel.setEnabled(on)
        if on:
            self.progress.setRange(0, 0)
            self.progress.setFormat(title)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("")

    def _on_progress(self, done: int, total: int, msg: str) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.progress.setFormat(f"{msg} %v / %m")

    def cancel_task(self) -> None:
        if self.task is not None and self.task.isRunning():
            self.task.cancel()

    # ================================================================ прочее
    def set_dark(self, on: bool) -> None:
        on = bool(on)
        apply_theme(on)
        self.settings["dark_theme"] = on
        self.a_dark.blockSignals(True)
        self.a_dark.setChecked(on)
        self.a_dark.blockSignals(False)
        self.canvas.set_dark(on)
        self.browser.set_dark(on)

    def show_error(self, text: str) -> None:
        self.statusBar().showMessage("✖ " + text.splitlines()[0], 10000)
        if os.environ.get("GFONT_NO_DIALOGS"):
            return
        QMessageBox.critical(self, "Ошибка", text)

    def _restore_window(self) -> None:
        g = self.settings["draw_geometry"]
        if g:
            try:
                self.restoreGeometry(QByteArray.fromBase64(g.encode()))
                return
            except Exception:  # noqa: BLE001
                pass
        self.resize(1500, 950)

    def closeEvent(self, ev) -> None:
        if self.task is not None and self.task.isRunning():
            self.task.cancel()
            self.task.wait(15000)
        if not self._ask_save_changes():
            ev.ignore()
            return
        self._remove_draft()
        self.settings["draw_geometry"] = bytes(self.saveGeometry().toBase64()).decode()
        self.settings.save()
        super().closeEvent(ev)
