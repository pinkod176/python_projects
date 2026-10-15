"""Экспорт проекта в .gfont и импорт .gfont в проект (без Qt).

Сборка — тем же кодом, что и в конвертере: шаблон читается gfont.format, записи
заменяются/добавляются gfont.build.write_glyphs, файл пишется атомарно и проверяется
gfont.build.save_and_validate (структура, коды, NaN, длина 10+4·nf+npts, нет пустых
основных букв/цифр/знаков).

Альтернативные записи (alt_mode = "plus32768"). По описанию формата варианты символа
лежат в кодах «код + 32768». Проверка эталонов этого НЕ подтвердила: там на этих кодах
обычные символы U+8000…U+FFFF (иероглифы: 0x8430 = «萰» — это «а» + 32768).
Поэтому по умолчанию варианты не пишутся; если включить, для каждого нарисованного
символа с кодом < 0x8000 в запись код + 32768 пишется вариант 2 (3, … по кругу),
а если вариантов нет — слегка изменённая копия основного (наклон/масштаб/дрожание по seed).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

from gfont.build import ConvertReport, save_and_validate, write_glyphs
from gfont.errors import Cancelled
from gfont.format import read_gfont
from gfont.session import default_template_path

from .charsets import ALL_CODES
from .project import DRAWN, GlyphEntry, Project
from .strokes import glyph_raw_g, glyph_to_gfont, normalize_factors, strokes_from_g, vary

ALT_OFFSET = 0x8000


@dataclass
class ExportOptions:
    output: str
    template: str = ""             # "" = встроенный шаблон
    remove_old: bool = True        # убрать буквы шаблона (< U+2000), которых нет в проекте
    normalize: bool = False
    alt_mode: str = "none"         # none | plus32768
    seed: int = 1


@dataclass
class ExportResult:
    report: ConvertReport
    output: str = ""
    by_user: List[int] = field(default_factory=list)
    auto: List[int] = field(default_factory=list)       # заполнены автоматически
    missing: List[int] = field(default_factory=list)    # из списка, но не нарисованы
    alt_written: List[int] = field(default_factory=list)

    def text(self) -> str:
        def chars(codes, limit=150):
            s = "".join(chr(c) for c in codes[:limit])
            return s + (f" … (+{len(codes) - limit})" if len(codes) > limit else "")

        L = [f"Файл: {self.output}",
             f"Нарисовано вами: {len(self.by_user)}",
             f"Заполнено автоматически (шрифт, похожие): {len(self.auto)}  {chars(self.auto)}",
             f"Нет (не нарисованы): {len(self.missing)}  {chars(self.missing)}"]
        if self.alt_written:
            L.append(f"Альтернативные записи (код + 32768): {len(self.alt_written)}")
        L.append("--- Сборка по шаблону ---")
        L.append(self.report.text())
        return "\n".join(L)


def project_gfont_glyphs(project: Project, normalize: bool = False) -> Dict[int, List]:
    """Все нарисованные глифы проекта в координатах .gfont (как будут записаны)."""
    geo = project.geometry()
    st = project.settings
    raw = {c: glyph_raw_g(e.strokes, geo, st.smoothing, st.density)
           for c, e in project.glyphs.items() if e.has_drawing()}
    factors = normalize_factors(raw, geo.tm) if normalize else {}
    out = {}
    for c, e in project.glyphs.items():
        if c not in raw:
            continue
        out[c] = glyph_to_gfont(e.strokes, geo, code=c, smoothing=st.smoothing, density=st.density,
                                autoalign=st.autoalign, factor=factors.get(c, 1.0))
    return out


def export_project(project: Project, opts: ExportOptions,
                   progress: Optional[Callable[[int, int], None]] = None,
                   cancel: Optional[Callable[[], bool]] = None) -> ExportResult:
    t0 = time.time()
    rep = ConvertReport(mode="рисунок вручную")
    geo = project.geometry()
    rep.scale = geo.k
    template = opts.template or str(default_template_path())
    gf = read_gfont(template)
    rep.template_entries = len(gf.entries)

    glyphs = project_gfont_glyphs(project, opts.normalize)
    st = project.settings
    res = ExportResult(rep, str(opts.output))
    for c in glyphs:
        (res.auto if project.glyphs[c].source in ("font", "similar") else res.by_user).append(c)
    res.missing = [c for c in ALL_CODES if c not in glyphs]

    total = len(glyphs)
    if opts.alt_mode == "plus32768":
        for i, (c, strokes) in enumerate(list(glyphs.items())):
            if cancel is not None and cancel():
                raise Cancelled()
            if c >= ALT_OFFSET:
                continue
            e = project.glyphs[c]
            others = [v for v in e.variants[1:] if v]
            if others:
                alt = glyph_to_gfont(others[0], geo, code=c, smoothing=st.smoothing,
                                     density=st.density, autoalign=st.autoalign)
            else:
                alt = vary(strokes, np.random.default_rng([opts.seed, c]), 1.0)
            glyphs[c + ALT_OFFSET] = alt
            res.alt_written.append(c + ALT_OFFSET)
            if progress:
                progress(i + 1, total)

    if cancel is not None and cancel():
        raise Cancelled()
    scope = list(ALL_CODES) + [c + ALT_OFFSET for c in res.alt_written]
    produced = write_glyphs(gf, glyphs, rep, scope=[c for c in scope if c < ALT_OFFSET],
                            preserve_template_extra=not opts.remove_old,
                            drop_template_noncjk=opts.remove_old)
    if cancel is not None and cancel():
        raise Cancelled()
    save_and_validate(gf, opts.output, rep, produced)
    rep.seconds = time.time() - t0
    if progress:
        progress(total, total)
    return res


def import_gfont(path, project: Project, codes=None) -> List[int]:
    """Открыть .gfont в редакторе: штрихи символов из списка становятся штрихами проекта
    (fixed — их можно править: двигать точки, удалять штрихи). Возвращает коды."""
    gf = read_gfont(path)
    geo = project.geometry()
    wanted = set(codes if codes is not None else ALL_CODES)
    got = []
    for code in gf.codes():
        if code not in wanted:
            continue
        try:
            strokes = gf.strokes(code)
        except Exception:  # noqa: BLE001 — битая запись: пропускаем
            continue
        st = strokes_from_g([s for s in strokes if len(s) >= 2], geo)
        if not st:
            continue
        project.glyphs[code] = GlyphEntry([st], DRAWN, "gfont")
        got.append(code)
    if got:
        project.dirty = True
    return got
