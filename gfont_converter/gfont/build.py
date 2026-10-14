"""Сборка .gfont из TTF/OTF: извлечение, нормализация, запись, самопроверка."""

from __future__ import annotations

import json
import os
import sys
import time
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .charset import FALLBACKS, is_core, parse_charset
from .extract import ExtractParams, FontSource, GlyphShape, extract_glyph, is_single_line_font
from .format import GFont, read_gfont
from .normalize import TargetMetrics, font_scale, measure_font, place_glyph
from .validate import ValidationReport, validate_file


NONCJK_LIMIT = 0x2E80   # ниже — латиница, кириллица, греческий, символы; выше — CJK и т.п.


@dataclass
class ConvertOptions:
    font: str
    output: str
    template: str
    mode: str = "skeleton"                 # skeleton | outline | auto
    charset: str = "default"
    preserve_template_extra: bool = False
    no_new_entries: bool = False
    drop_template_noncjk: bool = False     # удалить все нетронутые записи шаблона < U+2E80
    variation: float = 0.0
    seed: int = 1
    jobs: int = 0                          # 0 = по числу ядер
    font_number: int = 0
    metrics: TargetMetrics = field(default_factory=TargetMetrics)
    extract: ExtractParams = field(default_factory=ExtractParams)


@dataclass
class ConvertReport:
    mode: str = ""
    font_metrics: dict = field(default_factory=dict)
    scale: float = 0.0
    replaced: List[int] = field(default_factory=list)       # заменены на месте
    new: List[int] = field(default_factory=list)            # новые коды (риск!)
    skipped_new: List[int] = field(default_factory=list)    # новые, но --no-new-entries
    fallback: Dict[int, int] = field(default_factory=dict)  # код -> чем заменён
    missing_in_font: List[int] = field(default_factory=list)
    empty_in_font: List[int] = field(default_factory=list)
    removed_template: List[int] = field(default_factory=list)
    kept_template: List[int] = field(default_factory=list)  # --preserve-template-extra
    dropped_noncjk: List[int] = field(default_factory=list) # --drop-template-noncjk
    untouched_noncjk: List[int] = field(default_factory=list)  # остались от шаблона (< U+2E80)
    template_entries: int = 0
    total_entries: int = 0
    seconds: float = 0.0
    validation: Optional[ValidationReport] = None

    def text(self) -> str:
        def chars(codes, limit=120):
            s = "".join(chr(c) for c in codes[:limit])
            return s + (f" ... (+{len(codes) - limit})" if len(codes) > limit else "")

        L = []
        L.append(f"Режим: {self.mode}; масштаб {self.scale:.4f} ед.gfont/ед.шрифта")
        fm = self.font_metrics
        if fm:
            L.append(f"Метрики шрифта: UPM {fm['upm']}, cap {fm['cap']:.0f}, x-height "
                     f"{fm['xheight']:.0f}, asc {fm['ascender']:.0f}, desc {fm['descender']:.0f}")
        L.append(f"Записей в шаблоне: {self.template_entries}; в результате: {self.total_entries}")
        L.append(f"Заменено на месте: {len(self.replaced)}  {chars(self.replaced)}")
        L.append(f"НОВЫЕ коды (их не было в шаблоне): {len(self.new)}  {chars(self.new)}")
        if self.skipped_new:
            L.append(f"Пропущены как новые (--no-new-entries): {len(self.skipped_new)}  "
                     f"{chars(self.skipped_new)}")
        if self.fallback:
            L.append("Подстановки: " + ", ".join(
                f"{chr(a)}(U+{a:04X})←{chr(b)}(U+{b:04X})" for a, b in self.fallback.items()))
        if self.missing_in_font:
            L.append(f"Нет в шрифте: {len(self.missing_in_font)}  {chars(self.missing_in_font)}")
        if self.empty_in_font:
            L.append(f"Пустые в шрифте: {len(self.empty_in_font)}  {chars(self.empty_in_font)}")
        if self.removed_template:
            L.append(f"Удалены старые записи шаблона (символ есть в charset, но не в шрифте): "
                     f"{len(self.removed_template)}  {chars(self.removed_template)}")
        if self.kept_template:
            L.append(f"Оставлены записи шаблона (--preserve-template-extra): "
                     f"{len(self.kept_template)}  {chars(self.kept_template)}")
        if self.dropped_noncjk:
            L.append(f"Удалены прочие старые записи шаблона < U+2E80 (--drop-template-noncjk): "
                     f"{len(self.dropped_noncjk)}  {chars(self.dropped_noncjk)}")
        if self.untouched_noncjk:
            L.append(f"ВНИМАНИЕ: остались нетронутые записи шаблона < U+2E80 (старый стиль, в с_клода "
                     f"они битые; убрать: --drop-template-noncjk): {len(self.untouched_noncjk)}  "
                     f"{chars(self.untouched_noncjk)}")
        L.append(f"Время: {self.seconds:.1f} c")
        if self.validation is not None:
            L.append("--- Самопроверка ---")
            L.append(self.validation.summary())
        return "\n".join(L)

    def to_json(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if k != "validation"}
        d["fallback"] = {str(k): v for k, v in self.fallback.items()}
        if self.validation is not None:
            d["validation"] = {"ok": self.validation.ok, "errors": self.validation.errors,
                               "warnings": self.validation.warnings}
        return d


# ---- параллельная обработка (работает и на Windows: функции верхнего уровня) ----

_W: dict = {}


def _worker_init(font_path: str, font_number: int) -> None:
    _W["src"] = FontSource(font_path, font_number)


def _worker(args) -> Tuple[int, GlyphShape]:
    code, src_code, mode, cap, params = args
    return code, extract_glyph(_W["src"], src_code, mode, cap, params)


def convert(opts: ConvertOptions, log=print) -> ConvertReport:
    t0 = time.time()
    rep = ConvertReport()
    gf = read_gfont(opts.template)
    rep.template_entries = len(gf.entries)
    src = FontSource(opts.font, opts.font_number)
    fm = measure_font(src)
    rep.font_metrics = asdict(fm)
    s = font_scale(fm, opts.metrics)
    rep.scale = s
    mode = opts.mode
    if mode == "auto":
        mode = "outline" if is_single_line_font(src) else "skeleton"
    rep.mode = mode
    if opts.extract.fill_spacing <= 0:
        opts.extract.fill_spacing = opts.metrics.fill_spacing / s

    codes = parse_charset(opts.charset)
    jobs: List[Tuple[int, int]] = []
    for code in codes:
        src_code = code if src.has(code) else None
        if src_code is None:
            for fb in FALLBACKS.get(code, []):
                if src.has(fb):
                    src_code = fb
                    rep.fallback[code] = fb
                    break
        if src_code is None:
            rep.missing_in_font.append(code)
            continue
        if code not in gf and opts.no_new_entries:
            rep.skipped_new.append(code)
            continue
        jobs.append((code, src_code))

    log(f"Символов к обработке: {len(jobs)} (режим {mode})")
    shapes: Dict[int, GlyphShape] = {}
    tasks = [(c, sc, mode, fm.cap, opts.extract) for c, sc in jobs]
    n_jobs = opts.jobs if opts.jobs > 0 else min(8, os.cpu_count() or 1)
    if n_jobs > 1 and len(tasks) > 20:
        with ProcessPoolExecutor(max_workers=n_jobs, initializer=_worker_init,
                                 initargs=(opts.font, opts.font_number)) as ex:
            for i, (code, shape) in enumerate(ex.map(_worker, tasks, chunksize=4), 1):
                shapes[code] = shape
                if i % 50 == 0:
                    log(f"  {i}/{len(tasks)}")
    else:
        for i, (code, sc, md, cap, prm) in enumerate(tasks, 1):
            shapes[code] = extract_glyph(src, sc, md, cap, prm)
            if i % 50 == 0:
                log(f"  {i}/{len(tasks)}")

    produced: List[int] = []
    for code, _ in jobs:
        shape = shapes[code]
        rng = np.random.default_rng([opts.seed, code]) if opts.variation > 0 else None
        strokes = place_glyph(shape, s, opts.metrics, opts.variation, rng) if not shape.empty else []
        if not any(len(st) >= 2 for st in strokes):
            rep.empty_in_font.append(code)
            continue
        if code in gf:
            rep.replaced.append(code)
        else:
            rep.new.append(code)
        gf.set_glyph(code, strokes)
        produced.append(code)

    # Старые записи шаблона для символов из charset, которых нет в шрифте
    leftover = [c for c in codes if c in gf and c not in set(produced)]
    prefix = set(gf.prefix_codes)
    for c in leftover:
        if opts.preserve_template_extra or c in prefix:
            rep.kept_template.append(c)
        else:
            gf.remove(c)
            rep.removed_template.append(c)

    produced_set = set(produced)
    for c in list(gf.codes()):
        if c >= NONCJK_LIMIT or c in produced_set or c in prefix or c in rep.kept_template:
            continue
        if opts.drop_template_noncjk:
            gf.remove(c)
            rep.dropped_noncjk.append(c)
        else:
            rep.untouched_noncjk.append(c)

    out_dir = os.path.dirname(os.path.abspath(opts.output))
    os.makedirs(out_dir, exist_ok=True)
    gf.save(opts.output)
    rep.total_entries = len(gf.entries)
    required = [c for c in produced if is_core(c)]
    rep.validation = validate_file(opts.output, required=required, strict_codes=set(produced))
    rep.seconds = time.time() - t0
    return rep


def save_report_json(rep: ConvertReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rep.to_json(), f, ensure_ascii=False, indent=1)
