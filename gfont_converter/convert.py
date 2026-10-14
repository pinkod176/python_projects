#!/usr/bin/env python
"""Конвертер шрифтов TTF/OTF в рукописный формат .gfont.

Примеры:
    python convert.py шрифт.ttf результат.gfont --template с_клода_дополненный.gfont --preview out.png
    python convert.py --calibrate калибровка.gfont --template с_клода_дополненный.gfont --preview cal.png
    python convert.py --validate результат.gfont
    python convert.py --inspect результат.gfont --sheet лист.png
"""

from __future__ import annotations

import argparse
import os
import sys

from gfont.build import ConvertOptions, convert, save_report_json
from gfont.calibrate import build_calibration
from gfont.charset import parse_charset
from gfont.extract import ExtractParams
from gfont.format import read_gfont
from gfont.normalize import TargetMetrics
from gfont.preview import DEFAULT_LINES, render_lines, render_sheet
from gfont.validate import validate_file


def _setup_console() -> None:
    # Кириллица в cmd/PowerShell
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="convert.py",
        description="TTF/OTF -> .gfont (осевые линии штрихов для рукописного приложения)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument("paths", nargs="*", help="ШРИФТ ВЫХОД (или один путь для --calibrate/--validate/--inspect)")
    act = p.add_argument_group("действия")
    act.add_argument("--calibrate", action="store_true", help="создать калибровочный .gfont (шрифт не нужен)")
    act.add_argument("--validate", action="store_true", help="только проверить указанный .gfont")
    act.add_argument("--inspect", action="store_true", help="нарисовать превью существующего .gfont")

    g = p.add_argument_group("основное")
    g.add_argument("--template", help="шаблон .gfont (обязателен для конвертации и калибровки)")
    g.add_argument("--mode", choices=["skeleton", "outline", "auto"], default="skeleton",
                   help="skeleton — центральная линия заливки (по умолчанию); outline — контуры как "
                        "штрихи; auto — outline для однолинейных шрифтов, иначе skeleton")
    g.add_argument("--charset", default="default",
                   help="набор символов: default, ascii, latin1, cyrillic, russian, digits, punct, "
                        "U+0400-U+04FF, chars:абв, @файл.txt, -исключение (через запятую)")
    g.add_argument("--preserve-template-extra", action="store_true",
                   help="не удалять записи шаблона для символов из charset, которых нет в шрифте")
    g.add_argument("--drop-template-noncjk", action="store_true",
                   help="удалить ВСЕ нетронутые записи шаблона с кодами < U+2000 (буквы латиницы, кириллицы, "
                        "греческого старого стиля); знаки, CJK и префикс не трогаются")
    g.add_argument("--no-new-entries", action="store_true",
                   help="не добавлять коды, которых нет в шаблоне (только замена на месте)")
    g.add_argument("--font-number", type=int, default=0, help="номер шрифта в .ttc")
    g.add_argument("--jobs", type=int, default=0, help="число процессов (0 = авто)")
    g.add_argument("--report", help="сохранить отчёт в JSON")

    m = p.add_argument_group("геометрия и подгонка")
    m.add_argument("--baseline", type=float, default=-85.0, help="Y базовой линии (по эталону ≈ -85)")
    m.add_argument("--cap-height", type=float, default=315.0, help="высота заглавных (≈ 315)")
    m.add_argument("--x-height", type=float, default=None, help="высота строчных для --size-by xheight (≈ 220)")
    m.add_argument("--size-by", choices=["cap", "xheight"], default="cap", help="масштабировать по заглавным или строчным")
    m.add_argument("--scale", type=float, default=1.0, help="ручной множитель размера")
    m.add_argument("--slant", type=float, default=0.0, help="наклон вправо, градусы")
    m.add_argument("--spacing", type=float, default=1.0,
                   help="множитель ширины глифа по X (грубая подгонка интервала, см. README)")
    m.add_argument("--no-hand-order", action="store_true",
                   help="не менять порядок и направление штрихов (по умолчанию — как при письме "
                        "рукой: сверху вниз/слева направо, петли против часовой, точки последними)")
    m.add_argument("--overhang", type=float, default=0.35,
                   help="строчные буквы: какая доля длины хвостов/флажков, торчащих вбок за основу "
                        "буквы, остаётся (1.0 = как в шрифте). Убирает дыры после «б», перед «у»")
    m.add_argument("--side-anchors", action="store_true",
                   help="ЭКСПЕРИМЕНТ: одиночные move-to на краях ширины символа из шрифта "
                        "(включать только если калибровка показала, что они невидимы и влияют на интервал)")
    m.add_argument("--variation", type=float, default=0.0, help="«живость» 0..1+: случайный наклон/масштаб/дрожание")
    m.add_argument("--seed", type=int, default=1, help="зерно случайности для --variation")
    m.add_argument("--step", type=float, default=25.0, help="шаг между точками (эталон ≈ 27)")
    m.add_argument("--smooth", type=float, default=3.0, help="сглаживание (сигма, ед. .gfont)")
    m.add_argument("--corner", type=float, default=40.0, help="излом, сохраняемый как угол, градусы")
    m.add_argument("--dot-radius", type=float, default=6.0, help="минимальный радиус спирали-точки")
    m.add_argument("--fill-spacing", type=float, default=9.0, help="шаг колец заливки крупных пятен (● ■ •)")

    x = p.add_argument_group("скелетизация")
    x.add_argument("--raster", type=int, default=1000, help="пикселей растра на em (больше — точнее, медленнее)")
    x.add_argument("--spur", type=float, default=1.2, help="удалять шипы короче этого × толщина штриха")
    x.add_argument("--end-extend", type=float, default=0.8, help="продление концов × полутолщина")
    x.add_argument("--snap", type=float, default=0.0, help="склеивать концы штрихов ближе N px растра")

    v = p.add_argument_group("превью")
    v.add_argument("--preview", help="PNG со строками текста, отрисованными ИЗ ЗАПИСАННОГО .gfont")
    v.add_argument("--preview-text", action="append",
                   help="своя строка для превью (можно несколько раз)")
    v.add_argument("--sheet", help="PNG-лист всех глифов charset (штрихи цветом, начало — зелёная точка)")
    v.add_argument("--pen", type=float, default=9.0, help="толщина пера в превью, ед. .gfont")
    v.add_argument("--gap", type=float, default=35.0, help="зазор между буквами в превью")
    return p


def metrics_from(a) -> TargetMetrics:
    return TargetMetrics(baseline=a.baseline, cap_height=a.cap_height, x_height=a.x_height,
                         size_by=a.size_by, scale=a.scale, slant_deg=a.slant, spacing=a.spacing,
                         step=a.step, smooth=a.smooth, corner_deg=a.corner,
                         dot_radius=a.dot_radius, fill_spacing=a.fill_spacing,
                         side_anchors=a.side_anchors, overhang=a.overhang,
                         hand_order=not a.no_hand_order)


def do_preview(path: str, a, title: str) -> None:
    gf = read_gfont(path)        # именно записанный файл
    xh = a.x_height or 220.0
    if a.preview:
        lines = a.preview_text or DEFAULT_LINES
        missing = render_lines(gf, lines, a.preview, pen=a.pen, gap=a.gap, baseline=a.baseline,
                               cap=a.cap_height, xheight=xh, title=title)
        print(f"Превью: {a.preview}" + (f" (нет в файле: {''.join(missing)})" if missing else ""))
    if a.sheet:
        codes = parse_charset(a.charset)
        codes = [c for c in codes if c in gf] if a.inspect else codes
        render_sheet(gf, codes, a.sheet, baseline=a.baseline, cap=a.cap_height, xheight=xh)
        print(f"Лист глифов: {a.sheet}")


def main(argv=None) -> int:
    _setup_console()
    a = build_parser().parse_args(argv)

    if a.validate or a.inspect:
        if len(a.paths) != 1:
            print("Укажите один файл .gfont", file=sys.stderr)
            return 2
        if a.validate:
            rep = validate_file(a.paths[0])
            print(rep.summary())
            if not (a.preview or a.sheet):
                return 0 if rep.ok else 1
        do_preview(a.paths[0], a, os.path.basename(a.paths[0]))
        return 0

    if not a.template:
        print("Нужен --template шаблон.gfont", file=sys.stderr)
        return 2
    tm = metrics_from(a)

    if a.calibrate:
        if len(a.paths) != 1:
            print("Использование: convert.py --calibrate ВЫХОД.gfont --template Т.gfont", file=sys.stderr)
            return 2
        out = a.paths[0]
        _, lines, written = build_calibration(a.template, out, tm)
        print(f"Калибровочный файл: {out}")
        print("Что заменено:")
        print("\n".join(lines))
        rep = validate_file(out, required=written, strict_codes=set(written))
        print(rep.summary())
        if a.preview:
            a.preview_text = a.preview_text or ["HxoI| HHHH xxxx oooo IIII ||||", "0123456789",
                                                "_____ ----- =====", "##### ab ab ab cdcdcd eded",
                                                "f g y Hy|xo"]
            do_preview(out, a, "Калибровка (раскладка превью приблизительная)")
        return 0 if rep.ok else 1

    if len(a.paths) != 2:
        print("Использование: convert.py ШРИФТ.ttf ВЫХОД.gfont --template Т.gfont [опции]", file=sys.stderr)
        return 2
    font, out = a.paths
    opts = ConvertOptions(
        font=font, output=out, template=a.template, mode=a.mode, charset=a.charset,
        preserve_template_extra=a.preserve_template_extra, no_new_entries=a.no_new_entries,
        drop_template_noncjk=a.drop_template_noncjk,
        variation=a.variation, seed=a.seed, jobs=a.jobs, font_number=a.font_number, metrics=tm,
        extract=ExtractParams(em_px=a.raster, spur_ratio=a.spur, end_extend=a.end_extend,
                              snap_px=a.snap))
    rep = convert(opts)
    print(rep.text())
    if a.report:
        save_report_json(rep, a.report)
        print(f"Отчёт JSON: {a.report}")
    do_preview(out, a, f"{os.path.basename(font)} -> {os.path.basename(out)}")
    return 0 if rep.validation is None or rep.validation.ok else 1


if __name__ == "__main__":
    sys.exit(main())
