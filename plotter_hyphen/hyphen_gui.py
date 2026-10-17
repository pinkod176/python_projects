"""Запуск окна: python hyphen_gui.py

Самопроверки (работают и в exe, результат пишется в файл):
    hyphen_gui.py --selftest  папка [шрифт.gfont]
    hyphen_gui.py --smoke-gui папка
"""

import sys


def run() -> int:
    args = sys.argv[1:]
    if args[:1] == ["--selftest"] and len(args) >= 2:
        from hyph.selftest import run_selftest
        return run_selftest(args[1], args[2] if len(args) > 2 else "")
    if args[:1] == ["--smoke-gui"] and len(args) >= 2:
        from hyph.selftest import run_smoke_gui
        return run_smoke_gui(args[1])
    from hyph.gui import main
    return main()


if __name__ == "__main__":
    sys.exit(run())
