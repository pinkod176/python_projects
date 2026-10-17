# -*- mode: python ; coding: utf-8 -*-
# Сборка: pyinstaller --noconfirm --clean PlotterHyphen.spec
# Результат: dist/PlotterHyphen.exe (один файл, без консоли)
from PyInstaller.utils.hooks import collect_data_files

# pyphen при импорте перебирает папку dictionaries — она нужна целиком
datas = collect_data_files("pyphen")

excludes = ["tkinter", "matplotlib", "numpy", "IPython", "pytest", "PIL",
            "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml",
            "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtMultimedia",
            "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf",
            "PySide6.QtNetwork", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtOpenGL"]

a = Analysis(
    ["hyphen_gui.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=["hyph.gui", "hyph.selftest"],
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
    name="PlotterHyphen",
    debug=False,
    strip=False,
    upx=False,
    console=False,          # --windowed
)
