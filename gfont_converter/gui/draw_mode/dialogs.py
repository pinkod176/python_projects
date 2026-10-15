"""Диалоги режима рисования: способ заполнения, просмотр кандидатов, экспорт."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget,
                               QListWidgetItem, QPushButton, QRadioButton, QSpinBox, QVBoxLayout)

from .charsets import label
from .export import ExportOptions
from .fill import Candidate
from .project import Project
from .render import thumb_pixmap
from .strokes import glyph_to_gfont


class FillModeDialog(QDialog):
    """Как заполнить недостающие символы: из шрифта, из похожих или оставить пустыми."""

    def __init__(self, missing: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Заполнить недостающие символы")
        self.choice: Optional[str] = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Не нарисовано символов: <b>{missing}</b>. Как их заполнить?"))
        for key, title, text in (
                ("font", "А. Взять из шрифта TTF/OTF…",
                 "Буквы шрифта через конвертер, размер подгоняется под ваш почерк."),
                ("similar", "Б. Повторить из похожих",
                 "‑ − – — из дефиса, ё = е + две точки, й = и + дужка, № = N + o, "
                 "одинаковые буквы кириллицы и латиницы (а↔a, Р↔P …)."),
                ("none", "В. Оставить пустыми", "Ничего не добавлять.")):
            b = QPushButton(title)
            b.setMinimumHeight(40)
            b.setStyleSheet("text-align: left; padding: 6px 12px; font-weight: bold;")
            b.clicked.connect(lambda _=False, k=key: self._pick(k))
            lay.addWidget(b)
            t = QLabel(text)
            t.setWordWrap(True)
            t.setStyleSheet("color: #888; margin-left: 14px; margin-bottom: 6px;")
            lay.addWidget(t)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _pick(self, k: str) -> None:
        self.choice = k
        self.accept()


class CandidatesDialog(QDialog):
    """Предварительный просмотр заполнения: миниатюры и галочки."""

    def __init__(self, project: Project, cands: Dict[int, Candidate], title: str, parent=None,
                 dark: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 560)
        self.cands = cands
        geo = project.geometry()
        st = project.settings
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Предлагается заполнить: <b>{len(cands)}</b>. Снимите галочки с тех, "
                             "что не нужны. Всё можно будет перерисовать или отменить (Ctrl+Z на символе)."))
        self.lw = QListWidget()
        self.lw.setViewMode(QListView.IconMode)
        self.lw.setIconSize(QSize(72, 72))
        self.lw.setGridSize(QSize(150, 112))
        self.lw.setResizeMode(QListView.Adjust)
        self.lw.setWordWrap(True)
        for code, c in cands.items():
            g = glyph_to_gfont(c.strokes, geo, code=code, smoothing=st.smoothing, density=st.density,
                               autoalign=st.autoalign)
            it = QListWidgetItem(QIcon(thumb_pixmap(g, chr(code), "empty", 72, dark)),
                                 f"{label(code)}\n{c.how}")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            it.setData(Qt.UserRole, code)
            it.setToolTip(f"U+{code:04X} {label(code)}: {c.how}")
            self.lw.addItem(it)
        lay.addWidget(self.lw, 1)
        row = QHBoxLayout()
        ball = QPushButton("Отметить все")
        bnone = QPushButton("Снять все")
        ball.clicked.connect(lambda: self._all(Qt.Checked))
        bnone.clicked.connect(lambda: self._all(Qt.Unchecked))
        row.addWidget(ball)
        row.addWidget(bnone)
        row.addStretch(1)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Применить отмеченные")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _all(self, state) -> None:
        for i in range(self.lw.count()):
            self.lw.item(i).setCheckState(state)

    def selected(self) -> Dict[int, Candidate]:
        out = {}
        for i in range(self.lw.count()):
            it = self.lw.item(i)
            if it.checkState() == Qt.Checked:
                code = int(it.data(Qt.UserRole))
                out[code] = self.cands[code]
        return out


class ExportDialog(QDialog):
    def __init__(self, project: Project, default_out: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Экспорт в .gfont")
        self.project = project
        st = project.settings
        user, auto, total = project.counts()
        lay = QVBoxLayout(self)
        missing = total - user - auto
        info = QLabel(f"Нарисовано вами: <b>{user}</b>, заполнено автоматически: <b>{auto}</b>, "
                      f"не нарисовано: <b>{missing}</b> из {total}.")
        info.setWordWrap(True)
        lay.addWidget(info)
        form = QFormLayout()
        row = QHBoxLayout()
        self.ed_out = QLineEdit(str(default_out))
        b = QPushButton("…")
        b.setFixedWidth(36)
        b.clicked.connect(self._choose_out)
        row.addWidget(self.ed_out, 1)
        row.addWidget(b)
        form.addRow("Файл:", row)
        trow = QHBoxLayout()
        self.template = st.template
        self.lbl_tpl = QLabel()
        bt = QPushButton("Выбрать…")
        bt.clicked.connect(self._choose_tpl)
        bd = QPushButton("Встроенный")
        bd.clicked.connect(lambda: self._set_tpl(""))
        trow.addWidget(self.lbl_tpl, 1)
        trow.addWidget(bt)
        trow.addWidget(bd)
        form.addRow("Шаблон:", trow)
        self._set_tpl(self.template)
        lay.addLayout(form)

        self.ch_remove = QCheckBox("Убрать из шаблона буквы старого стиля, которых нет в проекте")
        self.ch_remove.setChecked(st.remove_old)
        self.ch_remove.setToolTip("Латиница, кириллица, греческий и знаки шаблона, которые вы не нарисовали, "
                                  "удаляются: в файле останется только ваш почерк (иероглифы шаблона не трогаются)")
        lay.addWidget(self.ch_remove)
        self.rb_norm = QRadioButton("Нормализовать размеры (строчные к одной высоте, заглавные к одной)")
        self.rb_keep = QRadioButton("Сохранить как есть")
        grp = QButtonGroup(self)
        grp.addButton(self.rb_norm)
        grp.addButton(self.rb_keep)
        (self.rb_norm if st.normalize else self.rb_keep).setChecked(True)
        lay.addWidget(self.rb_keep)
        lay.addWidget(self.rb_norm)
        self.ch_alt = QCheckBox("Записать варианты в коды «код + 32768» (альтернативы)")
        self.ch_alt.setChecked(st.alt_mode == "plus32768")
        lay.addWidget(self.ch_alt)
        warn = QLabel("⚠ В эталонных файлах коды ≥ 32768 — это иероглифы (например, «а» + 32768 = «萰»), "
                      "а не альтернативы. Включайте, только если точно знаете, что ваше приложение "
                      "берёт оттуда варианты: иначе иероглифы шаблона заменятся вашими буквами.")
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #b36b00;")
        lay.addWidget(warn)
        srow = QHBoxLayout()
        srow.addWidget(QLabel("seed для копий-вариаций:"))
        self.sp_seed = QSpinBox()
        self.sp_seed.setRange(0, 999999)
        self.sp_seed.setValue(st.seed)
        srow.addWidget(self.sp_seed)
        srow.addStretch(1)
        lay.addLayout(srow)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Экспортировать")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(640, 0)

    def _set_tpl(self, path: str) -> None:
        self.template = path
        self.lbl_tpl.setText(Path(path).name if path else "встроенный (с_клода_дополненный)")

    def _choose_tpl(self) -> None:
        p, _ = QFileDialog.getOpenFileName(self, "Шаблон .gfont", "", "Файл .gfont (*.gfont)")
        if p:
            self._set_tpl(p)

    def _choose_out(self) -> None:
        p, _ = QFileDialog.getSaveFileName(self, "Сохранить .gfont", self.ed_out.text(),
                                           "Файл .gfont (*.gfont)")
        if p:
            if not p.lower().endswith(".gfont"):
                p += ".gfont"
            self.ed_out.setText(p)

    def _ok(self) -> None:
        if not self.ed_out.text().strip():
            return
        self.accept()

    def options(self) -> ExportOptions:
        out = self.ed_out.text().strip()
        if not out.lower().endswith(".gfont"):
            out += ".gfont"
        return ExportOptions(output=out, template=self.template, remove_old=self.ch_remove.isChecked(),
                             normalize=self.rb_norm.isChecked(),
                             alt_mode="plus32768" if self.ch_alt.isChecked() else "none",
                             seed=self.sp_seed.value())
