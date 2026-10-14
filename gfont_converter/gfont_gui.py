#!/usr/bin/env python
"""Точка входа GUI (и собранного GfontConverter.exe).

    python gfont_gui.py [шрифт.ttf]
    python gfont_gui.py --selftest ШРИФТ.ttf ПАПКА
    python gfont_gui.py --smoke-gui ШРИФТ.ttf ПАПКА
    python gfont_gui.py --cli ...аргументы convert.py...   (CLI внутри exe)
"""

import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()   # нужно для пула процессов в собранном exe
    args = sys.argv[1:]
    if args[:1] == ["--selftest"] and len(args) >= 3:
        from gui.selftest import run_engine_selftest
        return run_engine_selftest(args[1], args[2])
    if args[:1] == ["--smoke-gui"] and len(args) >= 3:
        from gui.selftest import run_gui_smoke
        return run_gui_smoke(args[1], args[2])
    if args[:1] == ["--cli"]:
        from convert import main as cli_main
        return cli_main(args[1:])
    from gui.app import run_app
    return run_app(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
