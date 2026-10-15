"""Список символов по группам-вкладкам: миниатюры, статус, прогресс «нарисовано N из M»."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QLabel, QListView, QListWidget, QListWidgetItem,
                               QProgressBar, QTabWidget, QVBoxLayout, QWidget)

from .charsets import GROUP_OF, GROUPS, label
from .project import DRAWN, SKIPPED, Project
from .render import thumb_pixmap

THUMB = 52
STATUS_TEXT = {"empty": "не нарисован", DRAWN: "нарисован", SKIPPED: "пропущен"}
SOURCE_TEXT = {"font": " (из шрифта)", "similar": " (из похожего)", "gfont": " (из .gfont)"}


class GlyphBrowser(QWidget):
    codeSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: Dict[int, QListWidgetItem] = {}
        self.lists: List[QListWidget] = []
        self.dark = False
        self._thumb_source: Optional[Callable[[int], Optional[list]]] = None
        self._project: Optional[Project] = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.lbl = QLabel()
        f = self.lbl.font()
        f.setBold(True)
        self.lbl.setFont(f)
        self.bar = QProgressBar()
        self.bar.setTextVisible(True)
        lay.addWidget(self.lbl)
        lay.addWidget(self.bar)
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.ElideNone)
        for title, chars in GROUPS:
            lw = QListWidget()
            lw.setViewMode(QListView.IconMode)
            lw.setIconSize(QSize(THUMB, THUMB))
            lw.setGridSize(QSize(THUMB + 12, THUMB + 22))
            lw.setResizeMode(QListView.Adjust)
            lw.setMovement(QListView.Static)
            lw.setUniformItemSizes(True)
            lw.setSelectionMode(QAbstractItemView.SingleSelection)
            lw.setWordWrap(False)
            for ch in chars:
                it = QListWidgetItem(ch)
                it.setData(Qt.UserRole, ord(ch))
                it.setTextAlignment(Qt.AlignHCenter)
                lw.addItem(it)
                self.items[ord(ch)] = it
            lw.currentItemChanged.connect(self._on_current)
            self.lists.append(lw)
            self.tabs.addTab(lw, title)
        lay.addWidget(self.tabs, 1)
        self.setMinimumWidth(300)

    def set_source(self, project: Project, thumb_source: Callable[[int], Optional[list]]) -> None:
        """thumb_source(code) -> штрихи .gfont для миниатюры (или None)."""
        self._project = project
        self._thumb_source = thumb_source
        self.refresh_all()

    def set_dark(self, dark: bool) -> None:
        self.dark = dark
        self.refresh_all()

    def refresh_all(self) -> None:
        for code in self.items:
            self.refresh(code, update_counts=False)
        self.update_counts()

    def refresh(self, code: int, update_counts: bool = True) -> None:
        it = self.items.get(code)
        if it is None or self._project is None:
            return
        e = self._project.glyphs.get(code)
        status = e.status if e else "empty"
        strokes = self._thumb_source(code) if (self._thumb_source and e and e.has_drawing()) else None
        auto = bool(e and e.source in ("font", "similar"))
        it.setIcon(QIcon(thumb_pixmap(strokes, chr(code), status, THUMB, self.dark, auto)))
        tip = f"{label(code)}   U+{code:04X} — {STATUS_TEXT.get(status, status)}"
        if e and status == DRAWN:
            tip += SOURCE_TEXT.get(e.source, "")
            if len([v for v in e.variants if v]) > 1:
                tip += f", вариантов: {len([v for v in e.variants if v])}"
        it.setToolTip(tip)
        if update_counts:
            self.update_counts()

    def update_counts(self) -> None:
        if self._project is None:
            return
        user, auto, total = self._project.counts()
        self.bar.setRange(0, total)
        self.bar.setValue(user + auto)
        self.bar.setFormat(f"нарисовано {user} из {total}" + (f" (+{auto} заполнено)" if auto else ""))
        skipped = sum(1 for c in self.items if self._project.status(c) == SKIPPED)
        self.lbl.setText("Символы" + (f" — пропущено {skipped}" if skipped else ""))

    def _on_current(self, cur, _prev) -> None:
        if cur is not None:
            self.codeSelected.emit(int(cur.data(Qt.UserRole)))

    def select(self, code: int) -> None:
        it = self.items.get(code)
        if it is None:
            return
        gi = GROUP_OF[code]
        if self.tabs.currentIndex() != gi:
            self.tabs.setCurrentIndex(gi)
        lw = self.lists[gi]
        if lw.currentItem() is not it:
            lw.blockSignals(True)
            lw.setCurrentItem(it)
            lw.blockSignals(False)
        lw.scrollToItem(it)
