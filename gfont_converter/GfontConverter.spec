# -*- mode: python ; coding: utf-8 -*-
# Сборка: pyinstaller --noconfirm --clean GfontConverter.spec
# Результат: dist/GfontConverter.exe (один файл, без консоли, со значком и встроенным шаблоном)
import sys
from PyInstaller.utils.hooks import collect_submodules

hidden = (collect_submodules("fontTools.ttLib.tables")
          + collect_submodules("skimage.morphology")
          + collect_submodules("skimage.measure")
          + collect_submodules("gui.draw_mode")
          + ["scipy.ndimage", "fontTools.pens.qtPen"])

excludes = ["tkinter", "matplotlib", "IPython", "pytest", "PySide6.QtWebEngineCore",
            "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick",
            "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts",
            "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtNetwork",
            "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtOpenGL",
            "dask", "pooch", "networkx", "imageio", "tifffile"]

a = Analysis(
    ["gfont_gui.py"],
    pathex=["."],
    datas=[("resources/с_клода_дополненный.gfont", "resources"),
           ("resources/icon.png", "resources"),
           ("resources/icon.ico", "resources"),
           ("resources/sample/DejaVuSans.ttf", "resources/sample"),
           ("resources/sample/LICENSE-DejaVu.txt", "resources/sample")],
    hiddenimports=hidden + ["convert"],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GfontConverter",
    debug=False,
    strip=False,
    upx=False,
    console=False,          # --windowed
    icon="resources/icon.ico",
)
