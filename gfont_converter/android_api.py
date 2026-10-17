"""Мост для Android-приложения (Chaquopy): конвертер и редактор почерка без Qt.

Kotlin вызывает функции этого модуля; аргументы — строки и числа, ответ — JSON-строка
{"ok": true, ...} или {"ok": false, "error": "текст для пользователя"}.
Вся логика — та же, что в настольной версии: gfont (конвертер, формат, сборка,
самопроверка) и gui.draw_mode (проект, обработка штрихов, отмена, шаблон, заполнение,
экспорт). Здесь только перевод в JSON и состояние одного открытого шрифта и проекта.
"""

from __future__ import annotations

import functools
import json
import os
import traceback
from pathlib import Path
import numpy as np

from gfont import __version__
from gfont.errors import Cancelled, UserError

_S: dict = {"files": None, "session": None, "project": None, "editor": None, "sample": None,
            "cands": {}}

DRAFT_NAME = "автосохранение.gfproj"


# ---------------------------------------------------------------- служебное
def _r(v, nd=1):
    """Округлить координаты (меньше JSON)."""
    return np.round(np.asarray(v, dtype=float), nd).tolist()


def _ok(**kw) -> str:
    return json.dumps({"ok": True, **kw}, ensure_ascii=False)


def api(fn):
    @functools.wraps(fn)
    def wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except Cancelled:
            return json.dumps({"ok": False, "cancelled": True, "error": "Отменено"}, ensure_ascii=False)
        except UserError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001 — показываем пользователю, подробности в журнал
            return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}",
                               "trace": traceback.format_exc()}, ensure_ascii=False)
    return wrap


def _progress(cb):
    """Kotlin-объект с методом onProgress(done, total) -> функция; isCancelled() -> отмена."""
    if cb is None:
        return None, None
    return (lambda d, t: cb.onProgress(int(d), int(t))), (lambda: bool(cb.isCancelled()))


@api
def init(files_dir: str, resources_dir: str) -> str:
    """files_dir — личная папка приложения; resources_dir — распакованные resources/."""
    os.environ["GFONT_RESOURCES"] = resources_dir
    from gfont.session import DEFAULT_TEMPLATE_NAME
    packed = Path(resources_dir) / "default_template.gfont"     # имя в assets — латиницей
    if packed.is_file():
        os.replace(packed, Path(resources_dir) / DEFAULT_TEMPLATE_NAME)
    _S["files"] = Path(files_dir)
    (_S["files"] / "drafts").mkdir(parents=True, exist_ok=True)
    import importlib
    for mod in ("scipy.ndimage", "skimage.morphology", "gfont.build", "gui.draw_mode.export"):
        importlib.import_module(mod)     # прогрев: первая загрузка библиотек долгая
    from gfont.session import default_template_path
    return _ok(version=__version__, template=str(default_template_path()),
               template_exists=default_template_path().exists())


# ================================================================ конвертер
def _params(params_json: str):
    from gfont.session import UiParams
    return UiParams.from_dict(json.loads(params_json or "{}"))


@api
def conv_presets() -> str:
    from gfont.session import CHARSET_PRESETS, DEFAULT_PREVIEW_TEXT, UiParams
    return _ok(presets=[[k, v[0]] for k, v in CHARSET_PRESETS.items()],
               defaults=UiParams().to_dict(), preview_text=DEFAULT_PREVIEW_TEXT)


@api
def conv_open_font(path: str) -> str:
    from gfont.session import FontSession
    s = FontSession(path)
    _S["session"] = s
    return _ok(family=s.family, glyphs=s.glyph_count)


@api
def conv_coverage(params_json: str) -> str:
    from gfont.charset import drawable, parse_charset
    s = _S["session"]
    if s is None:
        raise UserError("Сначала откройте шрифт.")
    codes = [c for c in parse_charset(_params(params_json).charset_spec()) if drawable(c)]
    have, miss = s.coverage(codes)
    return _ok(have=len(have), total=len(codes), missing="".join(chr(c) for c in miss[:60]))


@api
def conv_preview(text: str, params_json: str) -> str:
    s = _S["session"]
    if s is None:
        raise UserError("Сначала откройте шрифт.")
    p = _params(params_json)
    glyphs, warn = {}, {}
    for ch in dict.fromkeys(text):
        if ch.isspace():
            continue
        r = s.glyph(ord(ch), p)
        glyphs[ch] = [_r(st) for st in r.strokes]
        if r.warnings:
            warn[ch] = r.warnings
    tm = p.metrics()
    return _ok(glyphs=glyphs, warnings=warn, baseline=tm.baseline, cap=tm.cap_height)


@api
def conv_save(out_path: str, params_json: str, template_path: str, progress=None) -> str:
    from gfont.session import default_template_path
    s = _S["session"]
    if s is None:
        raise UserError("Сначала откройте шрифт.")
    prog, cancel = _progress(progress)
    tpl = template_path or str(default_template_path())
    rep = s.convert(_params(params_json), out_path, tpl, progress=prog, cancel=cancel,
                    log=lambda *a: None, jobs=1)
    ok = rep.validation is not None and rep.validation.ok
    return _ok(valid=ok, report=rep.text(), replaced=len(rep.replaced), new=len(rep.new),
               missing=len(rep.missing_in_font))


# ================================================================ редактор почерка
def _project():
    if _S["project"] is None:
        _new_project()
    return _S["project"]


def _new_project(project=None):
    from gui.draw_mode.editor import GlyphEditor
    from gui.draw_mode.project import Project
    from gui.draw_mode.template_core import SampleSource
    pr = project or Project()
    _S["project"] = pr
    ed = GlyphEditor(pr)
    _S["editor"] = ed
    if _S["sample"] is None:
        _S["sample"] = SampleSource()
    _apply_sample(pr)
    _S["cands"] = {}
    return pr


def _apply_sample(pr) -> None:
    st = pr.settings
    smp = _S["sample"]
    try:
        if st.hint_gfont and Path(st.hint_gfont).is_file():
            smp.set_gfont(st.hint_gfont)
        elif st.sample_font and Path(st.sample_font).is_file():
            smp.set_font(st.sample_font)
        else:
            smp.set_font(None)
    except UserError:
        smp.set_font(None)


def _draft() -> Path:
    return _S["files"] / "drafts" / DRAFT_NAME


@api
def draw_init() -> str:
    """Открыть режим рисования: черновик прошлого сеанса восстанавливается сам."""
    from gui.draw_mode.project import Project
    restored = False
    if _S["project"] is None:
        d = _draft() if _S["files"] else None
        if d is not None and d.is_file():
            try:
                _new_project(Project.load(d))
                _S["project"].path = None
                restored = True
            except UserError:
                _new_project()
        else:
            _new_project()
    return _ok(restored=restored, **_state())


def _state() -> dict:
    from gui.draw_mode.charsets import ALL_CODES
    pr = _project()
    user, auto, total = pr.counts()
    statuses = {}
    for c in ALL_CODES:
        e = pr.glyphs.get(c)
        if e is not None:
            statuses[str(c)] = [e.status, e.source, sum(1 for v in e.variants if v)]
    from dataclasses import asdict
    return {"counts": [user, auto, total], "statuses": statuses, "settings": asdict(pr.settings),
            "name": pr.path.name if pr.path else pr.name, "dirty": pr.dirty,
            "sample": _S["sample"].source_name if _S["sample"] else ""}


@api
def draw_state() -> str:
    return _ok(**_state())


@api
def draw_groups() -> str:
    from gui.draw_mode.charsets import GROUPS, label
    return _ok(groups=[[t, [ord(c) for c in chars], [label(ord(c)) for c in chars]] for t, chars in GROUPS])


@api
def draw_geometry() -> str:
    g = _project().geometry()
    return _ok(width=g.width, height=g.height, cap=g.cap, k=g.k, baseline=g.baseline,
               guides=[[n, y] for n, y in g.guides()], gfont_baseline=g.tm.baseline,
               gfont_cap=g.tm.cap_height)


@api
def draw_template(code: int) -> str:
    d = _S["sample"].describe(int(code), _project().geometry()) if _S["sample"] else None
    if d is None:
        return _ok(kind="none")
    d["polys"] = [_r(q) for q in d["polys"]]
    return _ok(**d)


@api
def draw_hint(code: int) -> str:
    h = _S["sample"].hint(int(code), _project().geometry()) if _S["sample"] else None
    if h is None:
        return _ok(lines=[], dots=[])
    return _ok(lines=[_r(q) for q in h.lines], dots=list(h.dots))


def _glyph() -> dict:
    from gui.draw_mode.editor import processed_cell
    ed = _S["editor"]
    pr = _project()
    strokes = ed.strokes()
    procs = processed_cell(strokes, pr)
    e = pr.glyphs.get(ed.code)
    return {"code": ed.code, "variant": ed.variant, "strokes": [_r(q) for q in procs],
            "dots": [s.dot for s in strokes], "status": e.status if e else "empty",
            "source": e.source if e else "", "nvariants": len(e.variants) if e else 1,
            "can_undo": ed.can_undo(), "can_redo": ed.can_redo(),
            "counts": list(pr.counts()), "dirty": pr.dirty}


@api
def draw_select(code: int, variant: int = 0) -> str:
    _project()
    _S["editor"].select(int(code), int(variant))
    return _ok(**_glyph())


@api
def draw_glyph() -> str:
    _project()
    return _ok(**_glyph())


@api
def draw_add_stroke(points_json: str, dot: bool) -> str:
    from gui.draw_mode.project import Stroke
    pts = [(float(x), float(y)) for x, y in json.loads(points_json)]
    if not pts:
        raise UserError("пустой штрих")
    _S["editor"].add_stroke(Stroke(pts[:1] if dot else pts, dot=bool(dot)))
    return _ok(**_glyph())


@api
def draw_edit(action: str, i: int = -1, j: int = -1, x: float = 0.0, y: float = 0.0) -> str:
    """undo | redo | delete_last | clear | delete_stroke(i) | begin_point(i) | move_point(i, j, x, y)."""
    ed = _S["editor"]
    if action == "undo":
        ed.undo()
    elif action == "redo":
        ed.redo()
    elif action == "delete_last":
        ed.delete_last()
    elif action == "clear":
        ed.clear()
    elif action == "delete_stroke":
        ed.delete_stroke(int(i))
    elif action == "begin_point":
        ed.begin_point_edit(int(i))
    elif action == "move_point":
        ed.move_point(int(i), int(j), float(x), float(y))
    else:
        raise UserError(f"неизвестное действие {action}")
    return _ok(**_glyph())


@api
def draw_skip(code: int) -> str:
    from gui.draw_mode.project import DRAWN, SKIPPED
    pr = _project()
    e = pr.entry(int(code))
    if e.status != DRAWN:
        e.status = SKIPPED
        pr.dirty = True
    return _ok(**_state())


@api
def draw_settings(settings_json: str) -> str:
    """Изменить настройки проекта (сглаживание, плотность, размер, видимость шаблона…)."""
    pr = _project()
    st = pr.settings
    d = json.loads(settings_json or "{}")
    if "size" in d:
        pr.set_size(float(d.pop("size")))
    for k, v in d.items():
        if hasattr(st, k):
            setattr(st, k, type(getattr(st, k))(v))
    pr.dirty = True
    return _ok(**_state())


@api
def draw_sample(path: str) -> str:
    """Шрифт-образец (TTF/OTF) или свой шаблон .gfont; пусто — встроенный DejaVu Sans."""
    pr = _project()
    st = pr.settings
    smp = _S["sample"]
    if not path:
        smp.set_font(None)
        st.sample_font = st.hint_gfont = ""
    elif path.lower().endswith(".gfont"):
        smp.set_gfont(path)
        st.hint_gfont, st.sample_font = path, ""
    else:
        smp.set_font(path)
        if smp.error:
            raise UserError(smp.error + "\nОставлен встроенный образец.")
        st.sample_font, st.hint_gfont = path, ""
    pr.dirty = True
    return _ok(sample=smp.source_name)


def _gfont_of(code: int):
    from gui.draw_mode.strokes import glyph_to_gfont
    pr = _project()
    e = pr.glyphs.get(code)
    if e is None or not e.has_drawing():
        return None
    st = pr.settings
    return glyph_to_gfont(e.strokes, pr.geometry(), code=code, smoothing=st.smoothing,
                          density=st.density, autoalign=st.autoalign)


@api
def draw_thumbs(codes_json: str) -> str:
    """Глифы .gfont (как в файле) для миниатюр и предпросмотра: {код: штрихи или null}."""
    out = {}
    for c in json.loads(codes_json):
        g = _gfont_of(int(c))
        out[str(c)] = [_r(s) for s in g] if g else None
    return _ok(glyphs=out)


@api
def draw_line(text: str) -> str:
    out = {}
    for ch in dict.fromkeys(text):
        if ch.isspace():
            continue
        g = _gfont_of(ord(ch))
        out[ch] = [_r(s) for s in g] if g else None
    from gui.draw_mode.strokes import ratio_warning
    pr = _project()
    drawn = {}
    for c, e in pr.glyphs.items():
        if e.has_drawing() and e.source in ("", "user"):
            g = _gfont_of(c)
            if g:
                drawn[c] = [np.asarray(s, dtype=float) for s in g if len(s) >= 2]
    return _ok(glyphs=out, warning=ratio_warning(drawn, pr.geometry().tm))


# ---- проект ----
@api
def draw_new() -> str:
    _new_project()
    _remove_draft()
    return _ok(**_state())


@api
def draw_open(path: str) -> str:
    from gui.draw_mode.project import Project
    _new_project(Project.load(path))
    return _ok(**_state())


@api
def draw_save(path: str) -> str:
    pr = _project()
    pr.save(path)
    pr.dirty = False
    return _ok(**_state())


@api
def draw_autosave() -> str:
    """Черновик в личной папке приложения (восстанавливается при следующем запуске)."""
    if _S["project"] is None or _S["files"] is None:
        return _ok(saved=False)
    _S["project"].save(_draft())
    return _ok(saved=True)


def _remove_draft() -> None:
    try:
        _draft().unlink()
    except (OSError, TypeError):
        pass


@api
def draw_import_gfont(path: str) -> str:
    from gui.draw_mode.export import import_gfont
    pr = _project()
    got = import_gfont(path, pr)
    pr.settings.template = str(path)
    pr.settings.remove_old = False
    _S["editor"].set_project(pr)
    return _ok(imported=len(got), **_state())


# ---- заполнение ----
def _cands_json(cands) -> dict:
    from gui.draw_mode.strokes import glyph_to_gfont
    pr = _project()
    st = pr.settings
    out = {}
    for code, c in cands.items():
        g = glyph_to_gfont(c.strokes, pr.geometry(), code=code, smoothing=st.smoothing,
                           density=st.density, autoalign=st.autoalign)
        out[str(code)] = {"how": c.how, "strokes": [_r(s) for s in g]}
    return out


def _missing():
    from gui.draw_mode.charsets import ALL_CODES
    pr = _project()
    return [c for c in ALL_CODES if not (pr.glyphs.get(c) and pr.glyphs[c].has_drawing())]


@api
def draw_fill_similar() -> str:
    from gui.draw_mode.fill import similar_candidates
    _S["cands"] = similar_candidates(_project(), _missing())
    return _ok(candidates=_cands_json(_S["cands"]))


@api
def draw_fill_font(font_path: str, fit: bool, progress=None) -> str:
    """fit=True — «заполнить недостающие» под размер почерка; False — образцы как заготовка."""
    from gui.draw_mode.fill import font_candidates
    prog, cancel = _progress(progress)
    _S["cands"] = font_candidates(font_path, _missing(), _project(), fit_to_user=bool(fit),
                                  progress=prog, cancel=cancel)
    return _ok(candidates=_cands_json(_S["cands"]))


@api
def draw_apply(codes_json: str) -> str:
    from gui.draw_mode.fill import apply_candidates
    want = {int(c) for c in json.loads(codes_json)}
    sel = {c: v for c, v in _S["cands"].items() if c in want}
    apply_candidates(_project(), sel)
    _S["cands"] = {}
    return _ok(applied=len(sel), **_state())


# ---- экспорт ----
@api
def draw_export(out_path: str, opts_json: str, progress=None) -> str:
    from gui.draw_mode.export import ExportOptions, export_project
    from gui.draw_mode.project import Project
    pr = _project()
    if not any(e.has_drawing() for e in pr.glyphs.values()):
        raise UserError("Нарисуйте хотя бы один символ.")
    d = json.loads(opts_json or "{}")
    st = pr.settings
    opts = ExportOptions(output=out_path, template=d.get("template", st.template),
                         remove_old=bool(d.get("remove_old", st.remove_old)),
                         normalize=bool(d.get("normalize", st.normalize)),
                         alt_mode=d.get("alt_mode", st.alt_mode), seed=int(d.get("seed", st.seed)))
    st.template, st.remove_old, st.normalize = opts.template, opts.remove_old, opts.normalize
    st.alt_mode, st.seed = opts.alt_mode, opts.seed
    prog, cancel = _progress(progress)
    snapshot = Project.from_dict(pr.to_dict())
    res = export_project(snapshot, opts, progress=prog, cancel=cancel)
    ok = res.report.validation is not None and res.report.validation.ok
    return _ok(valid=ok, by_user=len(res.by_user), auto=len(res.auto), missing=len(res.missing),
               missing_chars="".join(chr(c) for c in res.missing[:80]), text=res.text())


@api
def validate(path: str) -> str:
    from gfont.validate import validate_file
    rep = validate_file(path)
    return _ok(valid=rep.ok, summary=rep.summary())


def version() -> str:
    return __version__


def _debug_reset() -> None:
    """Для тестов: забыть шрифт и проект."""
    _S.update({"session": None, "project": None, "editor": None, "cands": {}})


