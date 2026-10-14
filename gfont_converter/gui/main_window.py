"""Главное окно GfontConverter."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QByteArray, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                               QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter,
                               QTabWidget, QToolButton, QVBoxLayout, QWidget)

from gfont import __version__
from gfont.charset import parse_charset
from gfont.errors import UserError
from gfont.format import read_gfont
from gfont.session import (CHARSET_PRESETS, DEFAULT_PREVIEW_TEXT, FontSession, UiParams,
                           default_template_path, make_calibration, resource_dir,
                           variant_paths)
from gfont.validate import validate_file

from .glyph_view import GlyphDetail, GlyphGrid
from .preview_widget import PreviewWidget
from .settings import AppSettings
from .workers import EngineThread, TaskWorker

FONT_EXTS = {".ttf", ".otf", ".ttc", ".otc", ".woff", ".woff2"}
MODES = [("Центральная линия (скелет)", "skeleton"), ("Контур", "outline"), ("Авто", "auto")]

ABOUT_HTML = """
<h3>GfontConverter</h3>
<p>Конвертер шрифтов TTF/OTF в формат <b>.gfont</b> рукописного приложения.
В .gfont хранятся не контуры букв, а <b>осевые линии штрихов</b> (путь ручки);
приложение рисует их пером постоянной толщины.</p>
<p><b>Формат</b> (всё big-endian, кроме ZIP): u32 version=5; u32 L; L байт непрозрачного блока;
u32 K; K записей глифов (копии zip-записей); затем обычный ZIP (deflate), имя записи =
десятичный код символа. Запись глифа: u16 code, u32 nf (=2·npts), nf×float32 (x,y),
u32 npts, npts байт флагов (0 — начало штриха, 1 — продолжение). Ось Y вниз,
базовая линия около −85, заглавные около 315, X по центру bbox.</p>
<p><b>Записи с кодами ≥ 32768</b> — это обычные символы U+8000…U+FFFF (иероглифы,
полноширинные знаки), а не «альтернативные начертания»: так показали эталонные файлы.</p>
<p><b>Неизвестно (проверяется калибровочным файлом):</b></p>
<ul>
<li>назначение непрозрачного блока L (копируется из шаблона как есть);</li>
<li>принимает ли приложение новые коды, которых не было в шаблоне;</li>
<li>как приложение считает межбуквенный интервал;</li>
<li>толщина пера;</li>
<li>учитываются ли одиночные точки (move-to) в ширине символа.</li>
</ul>
<p>Предпросмотр рисуется по штрихам из конвертации; раскладка строки в нём
приблизительная.</p>
"""


class Slider(QWidget):
    """Ползунок с подписью значения. value — float = int / factor."""
    changed = Signal(float)

    def __init__(self, lo: float, hi: float, value: float, fmt: str, factor: float = 1.0,
                 tooltip: str = ""):
        super().__init__()
        self.factor = factor
        self.fmt = fmt
        self.s = QSlider(Qt.Horizontal)
        self.s.setRange(int(round(lo * factor)), int(round(hi * factor)))
        self.lbl = QLabel()
        self.lbl.setMinimumWidth(52)
        self.lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.s, 1)
        lay.addWidget(self.lbl)
        self.s.valueChanged.connect(self._on)
        self.set_value(value)
        if tooltip:
            self.setToolTip(tooltip)

    def value(self) -> float:
        return self.s.value() / self.factor

    def set_value(self, v: float) -> None:
        self.s.blockSignals(True)
        self.s.setValue(int(round(v * self.factor)))
        self.s.blockSignals(False)
        self.lbl.setText(self.fmt.format(self.value()))

    def _on(self, _):
        self.lbl.setText(self.fmt.format(self.value()))
        self.changed.emit(self.value())


class MainWindow(QMainWindow):
    sigLoad = Signal(str)
    sigPreview = Signal(int, str, object, bool)
    sigAnalysis = Signal(int, object, object)

    def __init__(self, settings: Optional[AppSettings] = None):
        super().__init__()
        self.settings = settings or AppSettings()
        self.session: Optional[FontSession] = None
        self.task: Optional[TaskWorker] = None
        self.preview_id = 0
        self.analysis_gen = 0
        self._codes: List[int] = []
        self._loading = False
        self.last_report = None
        self.last_saved: List[Path] = []
        self.setWindowTitle(f"GfontConverter {__version__} — конвертер шрифтов в .gfont")
        icon = resource_dir() / "icon.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.setAcceptDrops(True)

        self.engine = EngineThread()
        w = self.engine.worker
        self.sigLoad.connect(w.loadFont)
        self.sigPreview.connect(w.requestPreview)
        self.sigAnalysis.connect(w.startAnalysis)
        w.sessionLoaded.connect(self._on_session)
        w.sessionFailed.connect(self._on_session_failed)
        w.previewReady.connect(self._on_preview)
        w.glyphReady.connect(self._on_glyph)
        w.analysisProgress.connect(self._on_analysis_progress)
        w.error.connect(self.log_error)

        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(300)
        self.debounce.timeout.connect(self.refresh)

        self._build_ui()
        self._build_menu()
        self._restore()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 6)

        # --- верх: шрифт и шаблон
        top = QFrame()
        top.setFrameShape(QFrame.StyledPanel)
        tl = QHBoxLayout(top)
        self.btn_open = QPushButton("Открыть…")
        self.btn_open.setToolTip("Выбрать файл шрифта (.ttf, .otf). Можно перетащить файл в окно.")
        self.btn_open.clicked.connect(self.open_font_dialog)
        self.lbl_font = QLabel("Шрифт не выбран — нажмите «Открыть…» или перетащите .ttf/.otf в окно")
        f = QFont()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 1)
        self.lbl_font.setFont(f)
        self.lbl_count = QLabel("")
        self.lbl_template = QLabel("")
        self.btn_template = QPushButton("Шаблон…")
        self.btn_template.setToolTip("Выбрать свой шаблон .gfont (по умолчанию — встроенный)")
        self.btn_template.clicked.connect(self.choose_template)
        self.btn_template_default = QToolButton()
        self.btn_template_default.setText("встроенный")
        self.btn_template_default.setToolTip("Вернуть встроенный шаблон")
        self.btn_template_default.clicked.connect(lambda: self.set_template(""))
        tl.addWidget(self.btn_open)
        col = QVBoxLayout()
        col.addWidget(self.lbl_font)
        col.addWidget(self.lbl_count)
        tl.addLayout(col, 1)
        tl.addWidget(self.lbl_template)
        tl.addWidget(self.btn_template)
        tl.addWidget(self.btn_template_default)
        root.addWidget(top)

        # --- середина: параметры | вкладки
        split = QSplitter(Qt.Horizontal)
        split.addWidget(self._build_params())
        split.addWidget(self._build_tabs())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([450, 950])
        root.addWidget(split, 1)

        # --- низ: сохранение, прогресс, журнал
        bottom = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить как .gfont…")
        self.btn_save.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_save.clicked.connect(self.save_dialog)
        self.btn_calib = QPushButton("Калибровочный файл…")
        self.btn_calib.setToolTip("Создать тестовый .gfont для проверки интервала, толщины пера "
                                  "и приёма новых символов в приложении")
        self.btn_calib.clicked.connect(self.calibration_dialog)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("")
        self.progress.setValue(0)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_task)
        self.btn_log = QToolButton()
        self.btn_log.setText("Журнал")
        self.btn_log.setCheckable(True)
        self.btn_log.setArrowType(Qt.DownArrow)
        self.btn_log.toggled.connect(self._toggle_log)
        bottom.addWidget(self.btn_save)
        bottom.addWidget(self.btn_calib)
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.btn_log)
        root.addLayout(bottom)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setMinimumHeight(120)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.log.setFont(mono)
        root.addWidget(self.log)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Готово")

    def _build_params(self) -> QWidget:
        box = QGroupBox("Параметры")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight)

        self.cb_mode = QComboBox()
        for title, key in MODES:
            self.cb_mode.addItem(title, key)
        self.cb_mode.setToolTip("Скелет — центральная линия заливки (обычные шрифты).\n"
                                "Контур — обводка контуров (контурные и однолинейные шрифты).\n"
                                "Авто — контур для однолинейных шрифтов, иначе скелет.")
        form.addRow("Режим:", self.cb_mode)

        self.cb_charset = QComboBox()
        for key, (title, _) in CHARSET_PRESETS.items():
            self.cb_charset.addItem(title, key)
        form.addRow("Символы:", self.cb_charset)
        self.ed_custom = QLineEdit()
        self.ed_custom.setPlaceholderText("Свой набор: впишите символы, например АБВабв123№")
        form.addRow("", self.ed_custom)
        self.lbl_cover = QLabel("")
        self.lbl_cover.setWordWrap(True)
        self.lbl_cover.setStyleSheet("color: #555;")
        form.addRow("", self.lbl_cover)

        self.sl_slant = Slider(-20, 30, 0, "{:+.0f}°", 1, "Наклон вправо (+) или влево (−)")
        self.sl_scale = Slider(50, 150, 100, "{:.0f} %", 1, "Размер букв")
        self.sl_spacing = Slider(70, 140, 100, "{:.0f} %", 1,
                                 "Ширина букв по горизонтали. Как приложение считает межбуквенный "
                                 "интервал, неизвестно — проверьте калибровочным файлом.")
        self.sl_density = Slider(50, 200, 100, "{:.0f} %", 1,
                                 "Плотность точек на штрихе (100 % ≈ шаг 25, как в эталоне)")
        self.sl_smooth = Slider(0, 8, 3, "{:.1f}", 10, "Сглаживание штрихов")
        self.sl_overhang = Slider(10, 100, 35, "{:.0f} %", 1,
                                  "Строчные буквы: насколько длинными оставить хвосты и флажки, "
                                  "торчащие вбок за основу буквы (флажок «б», хвост «у», «з», «j»).\n"
                                  "100 % — как в шрифте. Меньше — нет больших пробелов рядом с такими "
                                  "буквами: приложение ставит буквы по их крайним точкам.")
        form.addRow("Наклон:", self.sl_slant)
        form.addRow("Масштаб:", self.sl_scale)
        form.addRow("Интервал (ширина):", self.sl_spacing)
        form.addRow("Плотность точек:", self.sl_density)
        form.addRow("Сглаживание:", self.sl_smooth)
        form.addRow("Хвосты строчных:", self.sl_overhang)

        self.sl_live = Slider(0, 100, 0, "{:.0f} %", 1,
                              "Живость почерка: небольшой случайный наклон, масштаб и дрожание "
                              "каждого символа. Разные seed дают разные варианты.")
        self.sp_seed = QSpinBox()
        self.sp_seed.setRange(0, 999999)
        self.sp_seed.setValue(1)
        self.sp_seed.setToolTip("Зерно случайности для живости почерка")
        form.addRow("Живость почерка:", self.sl_live)
        form.addRow("Seed:", self.sp_seed)
        var_row = QHBoxLayout()
        self.sp_n = QSpinBox()
        self.sp_n.setRange(1, 50)
        self.sp_n.setValue(3)
        self.btn_variants = QPushButton("Сделать N вариантов…")
        self.btn_variants.setMinimumWidth(170)
        self.btn_variants.setToolTip("Создать N файлов с seed = seed, seed+1, …\n"
                                     "Имена: <ИмяШрифта>_1.gfont, <ИмяШрифта>_2.gfont …")
        self.btn_variants.clicked.connect(self.variants_dialog)
        var_row.addWidget(QLabel("N ="))
        var_row.addWidget(self.sp_n)
        var_row.addWidget(self.btn_variants, 1)
        form.addRow("Варианты:", var_row)

        self.ch_no_new = QCheckBox("Не добавлять новые символы, только заменять\nсуществующие в шаблоне")
        self.ch_no_new.setToolTip("Безопасный режим: приём приложением новых кодов не проверен.")
        self.ch_replace_old = QCheckBox("Удалять буквы шаблона, которых нет\nв шрифте (строго один почерк)")
        self.ch_replace_old.setChecked(False)
        self.ch_replace_old.setToolTip(
            "Выключено (по умолчанию): если в вашем шрифте нет какой-то буквы (например, «ё» или «ā»),\n"
            "останется буква из встроенного шаблона — почерк Caveat, выровненный по тем же меркам.\n"
            "Включено: такие буквы удаляются, в файле только почерк вашего шрифта.\n"
            "Знаки шаблона (№ √ Ⅰ ① …), иероглифы и служебные записи не трогаются никогда.\n"
            "Записи с кодами ≥ 32768 — это иероглифы, а не «альтернативные начертания».")
        form.addRow(self.ch_no_new)
        form.addRow(self.ch_replace_old)

        for sig in (self.cb_mode.currentIndexChanged, self.cb_charset.currentIndexChanged,
                    self.ed_custom.textChanged, self.sl_slant.changed, self.sl_scale.changed,
                    self.sl_spacing.changed, self.sl_density.changed, self.sl_smooth.changed,
                    self.sl_overhang.changed,
                    self.sl_live.changed, self.sp_seed.valueChanged, self.ch_no_new.toggled,
                    self.ch_replace_old.toggled):
            sig.connect(self.params_changed)
        self.cb_charset.currentIndexChanged.connect(self._update_custom_enabled)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(box)
        scroll.setMinimumWidth(440)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        # --- предпросмотр
        pw = QWidget()
        pl = QVBoxLayout(pw)
        row = QHBoxLayout()
        row.addWidget(QLabel("Текст для проверки:"))
        self.ed_text = QLineEdit(DEFAULT_PREVIEW_TEXT)
        self.ed_text.textChanged.connect(lambda _: self.debounce.start())
        row.addWidget(self.ed_text, 1)
        pl.addLayout(row)
        row2 = QHBoxLayout()
        self.ch_source = QCheckBox("Показать исходный шрифт для сравнения")
        self.ch_source.toggled.connect(self._view_changed)
        self.ch_guides = QCheckBox("Линии строки")
        self.ch_guides.setChecked(True)
        self.ch_guides.setToolTip("Базовая линия (красная), высота строчных (синяя), заглавных (серая)")
        self.ch_guides.toggled.connect(self._view_changed)
        self.sl_pen = Slider(1, 30, 9, "{:.0f}", 1, "Толщина пера — только для предпросмотра")
        self.sl_pen.changed.connect(self._view_changed)
        self.sl_zoom = Slider(8, 40, 16, "{:.0f}", 1, "Масштаб предпросмотра")
        self.sl_zoom.changed.connect(self._view_changed)
        row2.addWidget(self.ch_source)
        row2.addWidget(self.ch_guides)
        row2.addSpacing(12)
        row2.addWidget(QLabel("Толщина пера:"))
        row2.addWidget(self.sl_pen, 1)
        row2.addWidget(QLabel("Масштаб:"))
        row2.addWidget(self.sl_zoom, 1)
        pl.addLayout(row2)
        self.preview = PreviewWidget()
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(self.preview)
        sa.setStyleSheet("QScrollArea { background: white; }")
        pl.addWidget(sa, 1)
        hint = QLabel("Предпросмотр нарисован по штрихам конвертации (так будет в приложении). "
                      "Раскладка строки приблизительная: интервал считает само приложение.")
        hint.setStyleSheet("color: #777;")
        hint.setWordWrap(True)
        pl.addWidget(hint)
        self.tabs.addTab(pw, "Предпросмотр")

        # --- символы
        gw = QWidget()
        gl = QVBoxLayout(gw)
        grow = QHBoxLayout()
        self.lbl_analysis = QLabel("Символы появятся после загрузки шрифта")
        self.ch_only_warn = QCheckBox("только сомнительные ⚠")
        self.ch_only_warn.toggled.connect(self._filter_grid)
        grow.addWidget(self.lbl_analysis, 1)
        grow.addWidget(self.ch_only_warn)
        gl.addLayout(grow)
        gsplit = QSplitter(Qt.Horizontal)
        self.grid = GlyphGrid()
        self.grid.glyphSelected.connect(self._show_glyph)
        self.detail = GlyphDetail()
        gsplit.addWidget(self.grid)
        gsplit.addWidget(self.detail)
        gsplit.setSizes([520, 420])
        gl.addWidget(gsplit, 1)
        self.tabs.addTab(gw, "Символы")
        return self.tabs

    def _build_menu(self) -> None:
        m = self.menuBar().addMenu("&Файл")
        a = QAction("Открыть шрифт…", self)
        a.setShortcut(QKeySequence.Open)
        a.triggered.connect(self.open_font_dialog)
        m.addAction(a)
        a = QAction("Выбрать шаблон .gfont…", self)
        a.triggered.connect(self.choose_template)
        m.addAction(a)
        a = QAction("Встроенный шаблон", self)
        a.triggered.connect(lambda: self.set_template(""))
        m.addAction(a)
        m.addSeparator()
        a = QAction("Сохранить как .gfont…", self)
        a.setShortcut(QKeySequence.Save)
        a.triggered.connect(self.save_dialog)
        m.addAction(a)
        a = QAction("Сделать N вариантов…", self)
        a.triggered.connect(self.variants_dialog)
        m.addAction(a)
        a = QAction("Калибровочный файл…", self)
        a.triggered.connect(self.calibration_dialog)
        m.addAction(a)
        a = QAction("Проверить .gfont…", self)
        a.triggered.connect(self.validate_dialog)
        m.addAction(a)
        m.addSeparator()
        a = QAction("Выход", self)
        a.triggered.connect(self.close)
        m.addAction(a)
        h = self.menuBar().addMenu("&Справка")
        a = QAction("О программе", self)
        a.triggered.connect(self.about)
        h.addAction(a)

    # ------------------------------------------------------------ настройки
    def _restore(self) -> None:
        s = self.settings
        p = UiParams.from_dict(s["params"])
        self._loading = True
        self.set_params(p)
        if s["preview_text"]:
            self.ed_text.setText(s["preview_text"])
        self.sl_pen.set_value(float(s["pen_width"]))
        self.ch_guides.setChecked(bool(s["show_guides"]))
        self.ch_source.setChecked(bool(s["show_source"]))
        self.sp_n.setValue(int(s["variants_n"]))
        self.btn_log.setChecked(bool(s["log_open"]))
        self._toggle_log(bool(s["log_open"]))
        if s["params_version"] != 2:
            # раньше флажок старых начертаний был включён по умолчанию (шаблон был битым)
            self.ch_replace_old.setChecked(False)
            s["params_version"] = 2
        if s["geometry"]:
            try:
                self.restoreGeometry(QByteArray.fromBase64(s["geometry"].encode()))
            except Exception:  # noqa: BLE001
                pass
        else:
            self.resize(1400, 900)
        self._loading = False
        self.set_template(s["template"] or "", quiet=True)
        self._update_custom_enabled()
        self._view_changed()
        last = s["last_font"]
        if last and Path(last).is_file():
            self.load_font(last)

    def store_settings(self) -> None:
        s = self.settings
        s["params"] = self.params().to_dict()
        s["preview_text"] = self.ed_text.text()
        s["pen_width"] = self.sl_pen.value()
        s["show_guides"] = self.ch_guides.isChecked()
        s["show_source"] = self.ch_source.isChecked()
        s["variants_n"] = self.sp_n.value()
        s["log_open"] = self.btn_log.isChecked()
        s["geometry"] = bytes(self.saveGeometry().toBase64()).decode()
        s.save()

    def params(self) -> UiParams:
        return UiParams(
            mode=self.cb_mode.currentData(), charset_preset=self.cb_charset.currentData(),
            custom_chars=self.ed_custom.text(), slant=self.sl_slant.value(),
            scale=self.sl_scale.value() / 100.0, spacing=self.sl_spacing.value() / 100.0,
            density=self.sl_density.value() / 100.0, smooth=self.sl_smooth.value(),
            overhang=self.sl_overhang.value() / 100.0,
            liveliness=self.sl_live.value() / 100.0, seed=self.sp_seed.value(),
            no_new_entries=self.ch_no_new.isChecked(),
            replace_old=self.ch_replace_old.isChecked())

    def set_params(self, p: UiParams) -> None:
        self.cb_mode.setCurrentIndex(max(0, self.cb_mode.findData(p.mode)))
        self.cb_charset.setCurrentIndex(max(0, self.cb_charset.findData(p.charset_preset)))
        self.ed_custom.setText(p.custom_chars)
        self.sl_slant.set_value(p.slant)
        self.sl_scale.set_value(p.scale * 100)
        self.sl_spacing.set_value(p.spacing * 100)
        self.sl_density.set_value(p.density * 100)
        self.sl_smooth.set_value(p.smooth)
        self.sl_overhang.set_value(p.overhang * 100)
        self.sl_live.set_value(p.liveliness * 100)
        self.sp_seed.setValue(p.seed)
        self.ch_no_new.setChecked(p.no_new_entries)
        self.ch_replace_old.setChecked(p.replace_old)

    # -------------------------------------------------------------- шаблон
    def template_path(self) -> Path:
        t = self.settings["template"]
        return Path(t) if t else default_template_path()

    def set_template(self, path: str, quiet: bool = False) -> None:
        if path:
            try:
                gf = read_gfont(path)
            except UserError as exc:
                if not quiet:
                    self.show_error(str(exc))
                path = ""
            else:
                self.log_line(f"Шаблон: {path} ({len(gf.entries)} записей)")
        self.settings["template"] = path
        p = self.template_path()
        name = p.name if path else f"встроенный ({p.name})"
        self.lbl_template.setText(f"Шаблон: {name}")
        self.lbl_template.setToolTip(str(p))
        if not p.exists():
            self.lbl_template.setText("Шаблон: НЕ НАЙДЕН — выберите файл")
            self.lbl_template.setStyleSheet("color: #c00;")
        else:
            self.lbl_template.setStyleSheet("")

    def choose_template(self) -> None:
        start = str(self.template_path().parent)
        path, _ = QFileDialog.getOpenFileName(self, "Шаблон .gfont", start, "Шаблон (*.gfont)")
        if path:
            self.set_template(path)

    # -------------------------------------------------------------- шрифт
    def open_font_dialog(self) -> None:
        start = self.settings["last_font_dir"] or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть шрифт", start, "Шрифты (*.ttf *.otf *.ttc *.otc *.woff *.woff2);;Все файлы (*)")
        if path:
            self.load_font(path)

    def load_font(self, path: str) -> None:
        self.settings["last_font_dir"] = str(Path(path).parent)
        self.lbl_font.setText(f"Открываю {Path(path).name}…")
        self.statusBar().showMessage("Загрузка шрифта…")
        self.sigLoad.emit(str(path))

    def _on_session(self, session: FontSession) -> None:
        self.session = session
        self.settings["last_font"] = str(session.path)
        self.lbl_font.setText(f"{session.family}  —  {session.path.name}")
        self.lbl_font.setToolTip(str(session.path))
        self.log_line(f"Открыт шрифт: {session.path} ({session.family}), символов в шрифте: "
                      f"{session.glyph_count}")
        self.statusBar().showMessage("Шрифт загружен")
        self._codes = []
        self.refresh()

    def _on_session_failed(self, msg: str) -> None:
        self.lbl_font.setText("Шрифт не открыт")
        self.statusBar().showMessage("Ошибка загрузки шрифта")
        self.show_error(msg)

    def dragEnterEvent(self, ev) -> None:
        urls = ev.mimeData().urls() if ev.mimeData().hasUrls() else []
        if any(Path(u.toLocalFile()).suffix.lower() in FONT_EXTS for u in urls):
            ev.acceptProposedAction()

    def dropEvent(self, ev) -> None:
        for u in ev.mimeData().urls():
            p = u.toLocalFile()
            if Path(p).suffix.lower() in FONT_EXTS:
                self.load_font(p)
                ev.acceptProposedAction()
                return

    # ----------------------------------------------- предпросмотр и анализ
    def _update_custom_enabled(self) -> None:
        self.ed_custom.setEnabled(self.cb_charset.currentData() == "custom")

    def params_changed(self, *_) -> None:
        if self._loading:
            return
        self.debounce.start()

    def _view_changed(self, *_) -> None:
        self.preview.set_options(pen=self.sl_pen.value(), guides=self.ch_guides.isChecked(),
                                 source=self.ch_source.isChecked(),
                                 zoom=self.sl_zoom.value() / 100.0)
        if self.ch_source.isChecked() and self.session and not self.preview.outlines:
            self.debounce.start()

    def refresh(self) -> None:
        """Перезапросить предпросмотр и анализ символов (в фоне)."""
        if self.session is None:
            return
        p = self.params()
        self.settings["params"] = p.to_dict()
        # предпросмотр
        self.preview_id += 1
        self.engine.worker.latest_preview = self.preview_id
        self.preview.busy = True
        self.preview.update()
        self.sigPreview.emit(self.preview_id, self.ed_text.text(), p, self.ch_source.isChecked())
        # анализ всех символов набора
        try:
            codes = parse_charset(p.charset_spec())
        except Exception as exc:  # noqa: BLE001
            self.lbl_cover.setText(f"Ошибка в наборе символов: {exc}")
            return
        have, miss = self.session.coverage(codes)
        txt = f"В шрифте есть {len(have)} из {len(codes)} символов набора."
        if miss:
            sample = " ".join(chr(c) for c in miss[:40])
            txt += f" Нет: {sample}{' …' if len(miss) > 40 else ''}"
        if not have:
            txt = "⚠ В шрифте нет ни одного символа из выбранного набора!"
        self.lbl_cover.setText(txt)
        self.lbl_count.setText(f"Символов в шрифте: {self.session.glyph_count}; "
                               f"в выбранном наборе есть: {len(have)} из {len(codes)}")
        if codes != self._codes:
            self._codes = codes
            self.grid.reset_codes(codes, p.metrics())
        self.grid.tm = p.metrics()
        self.analysis_gen += 1
        self.engine.worker.latest_analysis = self.analysis_gen
        self.sigAnalysis.emit(self.analysis_gen, codes, p)

    def _on_preview(self, req_id: int, data: dict) -> None:
        if req_id != self.preview_id:
            return
        self.preview.set_result(data["text"], data["glyphs"], data["outlines"],
                                data["params"].metrics())

    def _on_glyph(self, gen: int, r) -> None:
        if gen != self.analysis_gen:
            return
        self.grid.update_glyph(r, self.params().metrics())
        if self.ch_only_warn.isChecked():
            it = self.grid.items.get(r.code)
            if it is not None:
                it.setHidden(not r.warnings)

    def _on_analysis_progress(self, gen: int, done: int, total: int) -> None:
        if gen != self.analysis_gen:
            return
        warn = len(self.grid.warning_codes())
        if done < total:
            self.lbl_analysis.setText(f"Анализ символов: {done} / {total}…  сомнительных: {warn}")
        else:
            self.lbl_analysis.setText(f"Готово: {total} символов, сомнительных ⚠: {warn}. "
                                      "Выберите символ, чтобы увидеть точки и направление штрихов.")

    def _filter_grid(self, only: bool) -> None:
        for code, it in self.grid.items.items():
            r = self.grid.results.get(code)
            it.setHidden(bool(only) and not (r is not None and r.warnings))

    def _show_glyph(self, code: int) -> None:
        r = self.grid.results.get(code)
        if r is None:
            return
        outline = None
        if self.ch_source.isChecked():
            ch = chr(code)
            outline = self.preview.outlines.get(ch)
        self.detail.set_glyph(r, self.params().metrics(), outline)

    # ------------------------------------------------------- длительные операции
    def _busy(self, on: bool, title: str = "") -> None:
        for w in (self.btn_save, self.btn_variants, self.btn_calib, self.btn_open,
                  self.btn_template):
            w.setEnabled(not on)
        self.btn_cancel.setEnabled(on)
        if on:
            self.progress.setRange(0, 0)
            self.progress.setFormat(title)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("")

    def run_task(self, fn, title: str, on_done) -> TaskWorker:
        if self.task is not None and self.task.isRunning():
            self.show_error("Уже выполняется другая операция. Дождитесь её окончания или нажмите «Отмена».")
            return self.task
        self.log_line(f"▶ {title}")
        t = TaskWorker(fn, title)
        t.progress.connect(self._on_task_progress)
        t.logLine.connect(self.log_line)
        t.succeeded.connect(on_done)
        t.failed.connect(self._on_task_failed)
        t.cancelled.connect(self._on_task_cancelled)
        t.finished.connect(lambda: self._busy(False))
        self.task = t
        self._busy(True, title)
        t.start()
        return t

    def cancel_task(self) -> None:
        if self.task is not None and self.task.isRunning():
            self.task.cancel()
            self.btn_cancel.setEnabled(False)
            self.log_line("Отмена… (дождитесь завершения текущего шага)")

    def _on_task_progress(self, done: int, total: int, msg: str) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.progress.setFormat(f"{msg} %v / %m" if msg else "%v / %m")

    def _on_task_failed(self, msg: str) -> None:
        self.log_line("✖ " + msg)
        self.show_error(msg)

    def _on_task_cancelled(self) -> None:
        self.log_line("Операция отменена пользователем. Недописанные файлы не сохраняются.")
        self.statusBar().showMessage("Отменено")

    def _need_session(self) -> bool:
        if self.session is None:
            self.show_error("Сначала откройте шрифт (кнопка «Открыть…» или перетащите файл в окно).")
            return False
        if not self.template_path().exists():
            self.show_error(f"Шаблон не найден: {self.template_path()}. Выберите шаблон .gfont.")
            return False
        return True

    def _default_name(self) -> Path:
        folder = Path(self.settings["last_save_dir"] or self.session.path.parent)
        for p in variant_paths(folder, self.session.family, 999):
            if not p.exists():
                return p
        return folder / "font.gfont"

    def save_dialog(self) -> None:
        if not self._need_session():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как .gfont", str(self._default_name()),
                                              "Файл .gfont (*.gfont)")
        if not path:
            return
        if not path.lower().endswith(".gfont"):
            path += ".gfont"
        self.start_save(Path(path))

    def start_save(self, path: Path) -> TaskWorker:
        """Сохранение без диалога (используется и в смоук-тесте)."""
        self.settings["last_save_dir"] = str(path.parent)
        session, p, template = self.session, self.params(), self.template_path()

        def job(progress, cancel, log):
            return [(path, session.convert(p, path, template, cancel=cancel, log=log,
                                           progress=lambda d, t: progress(d, t, "Штрихи")))]
        return self.run_task(job, f"Сохранение {path.name}", self._on_saved)

    def variants_dialog(self) -> None:
        if not self._need_session():
            return
        n = self.sp_n.value()
        p = self.params()
        if p.liveliness <= 0:
            r = QMessageBox.question(
                self, "Варианты",
                "«Живость почерка» = 0 %, поэтому все варианты получатся одинаковыми.\n"
                "Установить живость 40 % и продолжить?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Yes:
                self.sl_live.set_value(40)
                p = self.params()
        folder = QFileDialog.getExistingDirectory(
            self, f"Папка для {n} вариантов", self.settings["last_save_dir"] or str(self.session.path.parent))
        if not folder:
            return
        paths = variant_paths(folder, self.session.family, n)
        existing = [x for x in paths if x.exists()]
        if existing:
            names = "\n".join(x.name for x in existing[:10])
            r = QMessageBox.question(self, "Файлы уже существуют",
                                     f"Будут перезаписаны файлы ({len(existing)}):\n{names}\n\nПерезаписать?",
                                     QMessageBox.Yes | QMessageBox.No)
            if r != QMessageBox.Yes:
                return
        self.start_variants(paths, p)

    def start_variants(self, paths: List[Path], p: UiParams) -> TaskWorker:
        self.settings["last_save_dir"] = str(paths[0].parent)
        session, template = self.session, self.template_path()

        def job(progress, cancel, log):
            out = []
            for i, path in enumerate(paths):
                if cancel():
                    from gfont.errors import Cancelled
                    raise Cancelled()
                pi = replace(p, seed=p.seed + i)
                log(f"Вариант {i + 1}/{len(paths)}: seed {pi.seed} → {path.name}")
                rep = session.convert(pi, path, template, cancel=cancel, log=log,
                                      progress=lambda d, t, i=i: progress(
                                          i * t + d, len(paths) * t, f"Вариант {i + 1}/{len(paths)}"))
                out.append((path, rep))
            return out
        return self.run_task(job, f"{len(paths)} вариантов", self._on_saved)

    def _on_saved(self, results) -> None:
        self.last_saved = [p for p, _ in results]
        bad = []
        for path, rep in results:
            self.last_report = rep
            self.log_line(f"=== {path} ===")
            self.log_line(rep.text())
            v = rep.validation
            self.log_line(
                f"Итого: основных записей (коды < 0x8000): {v.low_codes}; альтернативных: 0 "
                f"(в формате их нет — {v.high_codes} записей ≥ 0x8000 это иероглифы); "
                f"новых кодов: {len(rep.new)}; не удалось получить: "
                f"{len(rep.missing_in_font) + len(rep.empty_in_font)}")
            if not v.ok:
                bad.append(path)
        names = "\n".join(str(p) for p, _ in results)
        if bad:
            QMessageBox.warning(self, "Самопроверка не пройдена",
                                "Файлы записаны, но самопроверка нашла ошибки — см. журнал:\n"
                                + "\n".join(map(str, bad)))
        else:
            self.statusBar().showMessage(f"Сохранено: {len(results)} файл(ов), проверка OK")
            if not os.environ.get("GFONT_NO_DIALOGS"):
                QMessageBox.information(self, "Готово", f"Сохранено и проверено:\n{names}")

    def calibration_dialog(self) -> None:
        if not self.template_path().exists():
            self.show_error("Шаблон не найден — выберите шаблон .gfont.")
            return
        start = Path(self.settings["last_save_dir"] or Path.home()) / "калибровка.gfont"
        path, _ = QFileDialog.getSaveFileName(self, "Калибровочный файл", str(start),
                                              "Файл .gfont (*.gfont)")
        if not path:
            return
        if not path.lower().endswith(".gfont"):
            path += ".gfont"
        self.start_calibration(Path(path))

    def start_calibration(self, out: Path) -> TaskWorker:
        template, p = self.template_path(), self.params()

        def job(progress, cancel, log):
            _, lines, written = make_calibration(template, out, p)
            rep = validate_file(str(out), required=written, strict_codes=set(written))
            return out, lines, rep

        def done(res):
            out, lines, rep = res
            self.log_line(f"Калибровочный файл: {out}")
            self.log_line("\n".join(lines))
            self.log_line(rep.summary())
            self.last_saved = [out]
            if os.environ.get("GFONT_NO_DIALOGS"):
                return
            QMessageBox.information(
                self, "Калибровочный файл",
                f"Создан {out}\n\nЗагрузите его в приложение и наберите:\n"
                "HxoI|  HHHH xxxx oooo\n0123456789\n_____ ===== #####\nababab cdcdcd eded\nf g y\n\n"
                "Что означает каждый символ — в журнале.")
        return self.run_task(job, "Калибровочный файл", done)

    def validate_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Проверить .gfont", self.settings["last_save_dir"] or "",
                                              "Файл .gfont (*.gfont)")
        if not path:
            return
        self.run_task(lambda pr, c, log: validate_file(path), "Проверка файла",
                      lambda rep: (self.log_line(f"Проверка {path}:\n{rep.summary()}"),
                                   QMessageBox.information(self, "Проверка", rep.summary())))

    # ---------------------------------------------------------------- прочее
    def _toggle_log(self, on: bool) -> None:
        self.log.setVisible(on)
        self.btn_log.setArrowType(Qt.DownArrow if on else Qt.RightArrow)

    def log_line(self, text: str) -> None:
        self.log.appendPlainText(text)

    def log_error(self, text: str) -> None:
        self.log_line("✖ " + text)

    def show_error(self, text: str) -> None:
        self.log_line("✖ " + text)
        if os.environ.get("GFONT_NO_DIALOGS"):
            return
        QMessageBox.critical(self, "Ошибка", text)

    def about(self) -> None:
        QMessageBox.about(self, "О программе",
                          ABOUT_HTML.replace("<h3>GfontConverter</h3>",
                                             f"<h3>GfontConverter {__version__}</h3>"))

    def closeEvent(self, ev) -> None:
        if self.task is not None and self.task.isRunning():
            r = QMessageBox.question(self, "Идёт операция",
                                     "Идёт сохранение. Прервать и выйти?",
                                     QMessageBox.Yes | QMessageBox.No)
            if r != QMessageBox.Yes:
                ev.ignore()
                return
            self.task.cancel()
            self.task.wait(15000)
        self.store_settings()
        self.engine.stop()
        super().closeEvent(ev)
