"""Сборка .gfont из TTF/OTF: извлечение, нормализация, запись, самопроверка."""

from __future__ import annotations

import json
import multiprocessing
import os
import sys
import time
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, astuple, dataclass, field, replace
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .charset import FALLBACKS, is_core, parse_charset
from .extract import ExtractParams, FontSource, GlyphShape, extract_glyph, is_single_line_font
from .errors import Cancelled, UserError
from .format import GFont, read_gfont
from .normalize import TargetMetrics, font_scale, measure_font, place_glyph
from .validate import ValidationReport, validate_file


NONCJK_LIMIT = 0x2000   # ниже — буквы (латиница, кириллица, греческий…); выше — знаки, CJK


@dataclass
class ConvertOptions:
    font: str
    output: str
    template: str
    mode: str = "skeleton"                 # skeleton | outline | auto
    charset: str = "default"
    preserve_template_extra: bool = False
    no_new_entries: bool = False
    drop_template_noncjk: bool = False     # удалить все нетронутые записи шаблона < U+2000
    variation: float = 0.0
    seed: int = 1
    jobs: int = 0                          # 0 = по числу ядер
    font_number: int = 0
    metrics: TargetMetrics = field(default_factory=TargetMetrics)
    extract: ExtractParams = field(default_factory=ExtractParams)
    # --- для GUI (CLI их не задаёт) ---
    source: Optional[FontSource] = None    # уже открытый шрифт
    shape_cache: Optional[dict] = None     # кэш извлечённых форм (см. extract_shapes)
    progress: Optional[Callable[[int, int], None]] = None
    cancel: Optional[Callable[[], bool]] = None


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
    untouched_noncjk: List[int] = field(default_factory=list)  # остались от шаблона (< U+2000)
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
            L.append(f"Удалены прочие старые записи шаблона < U+2000 (--drop-template-noncjk): "
                     f"{len(self.dropped_noncjk)}  {chars(self.dropped_noncjk)}")
        if self.untouched_noncjk:
            L.append(f"ВНИМАНИЕ: остались нетронутые записи шаблона < U+2000 (старый стиль, в с_клода "
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


def _check(cancel) -> None:
    if cancel is not None and cancel():
        raise Cancelled()


def resolve_mode(src: FontSource, mode: str) -> str:
    if mode == "auto":
        return "outline" if is_single_line_font(src) else "skeleton"
    return mode


def effective_extract_params(p: ExtractParams, tm: TargetMetrics, s: float) -> ExtractParams:
    """Параметры извлечения с вычисленным шагом колец заливки (зависит от масштаба)."""
    q = replace(p)
    if q.fill_spacing <= 0:
        q.fill_spacing = tm.fill_spacing / s
    return q


def shape_key(src_code: int, mode: str, params: ExtractParams) -> tuple:
    return (src_code, mode) + astuple(params)


def extract_shapes(src: FontSource, src_codes: Iterable[int], mode: str, cap: float,
                   params: ExtractParams, *, jobs: int = 0, cache: Optional[dict] = None,
                   progress=None, cancel=None, log=print) -> Dict[int, GlyphShape]:
    """Извлечь формы глифов (самая дорогая часть). Общая для CLI и GUI.

    cache: словарь shape_key -> GlyphShape; найденное берётся из него, новое кладётся в него.
    progress(done, total) и cancel() -> bool вызываются между глифами.
    """
    src_codes = list(src_codes)
    out: Dict[int, GlyphShape] = {}
    todo = []
    for sc in src_codes:
        key = shape_key(sc, mode, params)
        if cache is not None and key in cache:
            out[sc] = cache[key]
        else:
            todo.append(sc)
    total = len(src_codes)
    done = total - len(todo)
    if progress:
        progress(done, total)

    def put(sc, shape):
        nonlocal done
        out[sc] = shape
        if cache is not None:
            cache[shape_key(sc, mode, params)] = shape
        done += 1
        if progress:
            progress(done, total)
        elif done % 50 == 0:
            log(f"  {done}/{total}")

    n_jobs = jobs if jobs > 0 else min(8, os.cpu_count() or 1)
    if n_jobs > 1 and len(todo) > 20:
        tasks = [(sc, sc, mode, cap, params) for sc in todo]
        # spawn везде (как на Windows): fork из многопоточного процесса (GUI) небезопасен
        ex = ProcessPoolExecutor(max_workers=n_jobs, initializer=_worker_init,
                                 initargs=(src.path, getattr(src, "font_number", 0)),
                                 mp_context=multiprocessing.get_context("spawn"))
        try:
            for sc, shape in ex.map(_worker, tasks, chunksize=4):
                put(sc, shape)
                _check(cancel)
        except Cancelled:
            ex.shutdown(wait=False, cancel_futures=True)
            raise
        else:
            ex.shutdown(wait=True)
    else:
        for sc in todo:
            _check(cancel)
            put(sc, extract_glyph(src, sc, mode, cap, params))
    return out


def convert(opts: ConvertOptions, log=print) -> ConvertReport:
    t0 = time.time()
    cancel = opts.cancel
    rep = ConvertReport()
    gf = read_gfont(opts.template)
    rep.template_entries = len(gf.entries)
    src = opts.source or FontSource(opts.font, opts.font_number)
    fm = measure_font(src)
    rep.font_metrics = asdict(fm)
    s = font_scale(fm, opts.metrics)
    rep.scale = s
    mode = resolve_mode(src, opts.mode)
    rep.mode = mode
    opts.extract = effective_extract_params(opts.extract, opts.metrics, s)

    codes = parse_charset(opts.charset)
    if not any(src.has(c) for c in codes):
        raise UserError("В шрифте нет ни одного символа из выбранного набора. "
                        "Выберите другой набор символов или другой шрифт.")
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
    _check(cancel)
    by_src = extract_shapes(src, sorted({sc for _, sc in jobs}), mode, fm.cap, opts.extract,
                            jobs=opts.jobs, cache=opts.shape_cache, progress=opts.progress,
                            cancel=cancel, log=log)
    shapes: Dict[int, GlyphShape] = {c: by_src[sc] for c, sc in jobs}
    _check(cancel)

    produced: List[int] = []
    for code, _ in jobs:
        _check(cancel)
        shape = shapes[code]
        rng = np.random.default_rng([opts.seed, code]) if opts.variation > 0 else None
        strokes = (place_glyph(shape, s, opts.metrics, opts.variation, rng,
                               lowercase=unicodedata.category(chr(code)) == "Ll",
                               xheight=fm.xheight)
                   if not shape.empty else [])
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

    _check(cancel)
    gf.save(opts.output)
    rep.total_entries = len(gf.entries)
    required = [c for c in produced if is_core(c)]
    rep.validation = validate_file(opts.output, required=required, strict_codes=set(produced))
    rep.seconds = time.time() - t0
    return rep


def save_report_json(rep: ConvertReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rep.to_json(), f, ensure_ascii=False, indent=1)
