"""Режим «Нарисовать свой почерк»: обработка штрихов, проект, экспорт, шаблон-подсказка, GUI."""

import os

import numpy as np
import pytest

from gfont.format import decode_glyph, encode_glyph, read_gfont
from gfont.validate import validate_file
from gui.draw_mode.charsets import ALL_CODES
from gui.draw_mode.export import ALT_OFFSET, ExportOptions, export_project, import_gfont, project_gfont_glyphs
from gui.draw_mode.fill import similar_candidates
from gui.draw_mode.geometry import CellGeometry
from gui.draw_mode.project import DRAWN, GlyphEntry, Project, Stroke
from gui.draw_mode.strokes import glyph_to_gfont, process_stroke, step_for


def circle(geo, cx=None, r=90, n=120, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    cx = geo.cx if cx is None else cx
    cy = geo.baseline - r
    t = np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, n)
    pts = np.stack([cx + r * np.cos(t), cy - r * np.sin(t)], axis=1) + rng.normal(0, noise, (n, 2))
    pts[-1] = pts[0]
    return [tuple(p) for p in pts]


def line(a, b, n=40, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, n)[:, None]
    pts = np.asarray(a) + (np.asarray(b) - np.asarray(a)) * t + rng.normal(0, noise, (n, 2))
    return [tuple(p) for p in pts]


def sample_project():
    pr = Project()
    g = pr.geometry()
    pr.glyphs[ord("о")] = GlyphEntry([[Stroke(circle(g, noise=0.8))]], DRAWN, "user")
    pr.glyphs[ord("е")] = GlyphEntry([[Stroke(circle(g, noise=0.8)[:100]),
                                       Stroke(line((g.cx - 85, g.baseline - 95), (g.cx + 85, g.baseline - 95)))]],
                                     DRAWN, "user")
    pr.glyphs[ord("Н")] = GlyphEntry([[Stroke(line((g.cx - 90, g.capline), (g.cx - 90, g.baseline), noise=0.5)),
                                       Stroke(line((g.cx + 90, g.capline), (g.cx + 90, g.baseline), noise=0.5)),
                                       Stroke(line((g.cx - 90, g.baseline - 190), (g.cx + 90, g.baseline - 190)))]],
                                     DRAWN, "user")
    pr.glyphs[ord("!")] = GlyphEntry([[Stroke(line((g.cx, g.capline), (g.cx, g.baseline - 70))),
                                       Stroke([(g.cx, g.baseline - 5)], dot=True)]], DRAWN, "user")
    pr.glyphs[ord("-")] = GlyphEntry([[Stroke(line((g.cx - 60, g.baseline - 120), (g.cx + 60, g.baseline - 120)))]],
                                     DRAWN, "user")
    return pr


# ------------------------------------------------------------ обработка штриха
def test_stroke_resampled_smoothed_and_ends_kept():
    g = CellGeometry()
    raw = line((300, 300), (300, 600), n=300, noise=1.5, seed=1)
    raw = raw + [raw[-1]] * 5                          # повторы последней точки
    q = process_stroke(Stroke(raw), g, smoothing=0.5, density=1.0)
    gr = g.to_g(raw)
    step = step_for(1.0)
    d = np.linalg.norm(np.diff(q, axis=0), axis=1)
    assert 0.6 * step < np.median(d) < 1.4 * step
    assert np.allclose(q[0], gr[0], atol=1e-6) and np.allclose(q[-1], gr[-1], atol=1e-6)
    # дрожание убрано: отклонение от прямой меньше, чем у сырых точек
    assert np.abs(q[:, 0] - q[:, 0].mean()).max() < np.abs(gr[:, 0] - gr[:, 0].mean()).max()


def test_density_changes_step():
    g = CellGeometry()
    raw = line((200, 300), (600, 300), n=200)
    a = process_stroke(Stroke(raw), g, 0.3, 1.0)
    b = process_stroke(Stroke(raw), g, 0.3, 2.0)
    assert len(b) > 1.6 * len(a)


def test_no_smoothing_keeps_corner():
    g = CellGeometry()
    raw = line((300, 300), (400, 600), 60) + line((400, 600), (500, 300), 60)[1:]
    q = process_stroke(Stroke(raw), g, smoothing=0.0, density=1.0)
    apex = g.to_g([(400, 600)])[0]
    assert np.min(np.linalg.norm(q - apex, axis=1)) < 1.0


def test_click_is_spiral_dot():
    g = CellGeometry()
    q = process_stroke(Stroke([(410.0, 500.0)], dot=True), g, 0.4, 1.0)
    assert 3 <= len(q) <= 6
    c = g.to_g([(410.0, 500.0)])[0]
    assert np.linalg.norm(q - c, axis=1).max() < 10
    # почти без движения — тоже точка
    q2 = process_stroke(Stroke([(410.0, 500.0), (410.5, 500.3)]), g, 0.4, 1.0)
    assert len(q2) == 6


def test_closed_loop_stays_closed():
    g = CellGeometry()
    q = process_stroke(Stroke(circle(g, noise=0.5)), g, 0.6, 1.0)
    assert np.allclose(q[0], q[-1])


def test_glyph_encode_decode_roundtrip():
    pr = sample_project()
    g = pr.geometry()
    for code, e in pr.glyphs.items():
        strokes = glyph_to_gfont(e.strokes, g, code=code, smoothing=0.4, density=1.0, autoalign=False)
        xs = [p[0] for s in strokes for p in s]
        assert abs(min(xs) + max(xs)) < 1e-6                 # X по центру bbox
        rec = encode_glyph(code, strokes)
        c2, back = decode_glyph(rec)
        assert c2 == code and len(back) == len(strokes)
        for a, b in zip(strokes, back):
            assert np.allclose(a, b, atol=1e-3)
        npts = sum(len(s) for s in strokes)
        assert len(rec) == 10 + 4 * 2 * npts + npts


def test_autoalign_pulls_to_baseline():
    g = CellGeometry()
    tm = g.tm
    raw = [Stroke(line((g.cx, g.capline), (g.cx, g.baseline - 25)))]
    a = glyph_to_gfont(raw, g, code=ord("l"), smoothing=0, density=1, autoalign=True)
    b = glyph_to_gfont(raw, g, code=ord("l"), smoothing=0, density=1, autoalign=False)
    assert abs(max(p[1] for s in a for p in s) - tm.baseline) < 1e-6
    assert max(p[1] for s in b for p in s) < tm.baseline - 15
    # нижний выносной элемент не трогаем
    c = glyph_to_gfont(raw, g, code=ord("р"), smoothing=0, density=1, autoalign=True)
    assert np.allclose(np.array(c[0]), np.array(b[0]))


# ------------------------------------------------------------ проект
def test_project_save_load_and_size(tmp_path):
    pr = sample_project()
    p = tmp_path / "почерк проект.gfproj"
    pr.save(p)
    back = Project.load(p)
    assert back.counts() == pr.counts()
    a = project_gfont_glyphs(pr)
    b = project_gfont_glyphs(back)
    for c in a:
        assert np.allclose(np.array(a[c][0]), np.array(b[c][0]), atol=0.05)
    # размер шаблона меняет разметку, а результат в .gfont остаётся прежним
    back.set_size(1.2)
    c2 = project_gfont_glyphs(back)
    for c in a:
        assert np.allclose(np.array(a[c][0]), np.array(c2[c][0]), atol=0.05)


# ------------------------------------------------------------ экспорт
def test_export_validate_and_reopen(tmp_path):
    pr = sample_project()
    out = tmp_path / "мой почерк.gfont"
    res = export_project(pr, ExportOptions(str(out)))
    assert res.report.validation.ok, res.text()
    assert validate_file(str(out)).ok
    assert sorted(res.by_user) == sorted(pr.glyphs)
    expected = project_gfont_glyphs(pr)
    gf = read_gfont(out)
    for c, strokes in expected.items():
        assert len(gf.strokes(c)) == len(strokes)
    # старые буквы шаблона (< U+2000), которых нет в проекте, убраны
    assert not [c for c in gf.codes() if c < 0x2000 and c not in pr.glyphs]
    # открыть в редакторе и экспортировать снова — те же штрихи
    pr2 = Project()
    got = import_gfont(out, pr2)
    assert set(got) == set(pr.glyphs)
    again = project_gfont_glyphs(pr2)
    for c in expected:
        for s1, s2 in zip(expected[c], again[c]):
            assert np.allclose(np.array(s1), np.array(s2), atol=0.01)


def test_template_layer_does_not_change_export(tmp_path):
    pr = sample_project()
    a, b = tmp_path / "a.gfont", tmp_path / "b.gfont"
    pr.settings.show_template = True
    pr.settings.show_order = True
    export_project(pr, ExportOptions(str(a)))
    pr.settings.show_template = False
    pr.settings.show_order = False
    pr.settings.template_opacity = 1.0
    export_project(pr, ExportOptions(str(b)))
    assert a.read_bytes() == b.read_bytes()


def test_alternates_default_off_keeps_high_codes(tmp_path):
    from gfont.session import default_template_path
    pr = sample_project()
    out = tmp_path / "x.gfont"
    export_project(pr, ExportOptions(str(out)))
    tpl, res = read_gfont(default_template_path()), read_gfont(out)
    for c in tpl.codes():
        if c >= ALT_OFFSET:
            assert res.raw(c) == tpl.raw(c)


def test_alternates_plus32768(tmp_path):
    from gfont.session import default_template_path
    pr = sample_project()
    g = pr.geometry()
    # у «о» два варианта: вариант 2 идёт в альтернативную запись
    pr.glyphs[ord("о")].variants.append([Stroke(circle(g, r=80, noise=0.8, seed=5))])
    out = tmp_path / "alt.gfont"
    res = export_project(pr, ExportOptions(str(out), alt_mode="plus32768", seed=7))
    assert res.report.validation.ok
    gf, tpl = read_gfont(out), read_gfont(default_template_path())
    for c in pr.glyphs:
        alt = c + ALT_OFFSET
        assert alt in res.alt_written and alt in gf
        assert gf.raw(alt)[2:] != gf.raw(c)[2:]                  # не копия основного
        if alt in tpl:
            assert gf.raw(alt) != tpl.raw(alt)                   # старая запись заменена
    o_alt = np.array(gf.strokes(ord("о") + ALT_OFFSET)[0])
    assert np.ptp(o_alt[:, 1]) < np.ptp(np.array(gf.strokes(ord("о"))[0])[:, 1])  # меньший круг


def test_similar_fill():
    pr = sample_project()
    c = similar_candidates(pr, ALL_CODES)
    assert len(c[ord("ё")].strokes) == len(pr.glyphs[ord("е")].strokes) + 2
    assert c[ord("ё")].strokes[-1].dot
    assert ord("o") in c and ord("e") in c and ord("H") in c        # латиница из кириллицы
    assert 0x2011 in c and 0x2014 in c
    w_dash = np.ptp([p[0] for s in c[0x2014].strokes for p in s.pts])
    w_hyph = np.ptp([p[0] for s in pr.glyphs[ord("-")].strokes for p in s.pts])
    assert w_dash > 2 * w_hyph


# ------------------------------------------------------------ шаблон-подсказка
@pytest.mark.parametrize("size", [0.8, 1.0, 1.2])
def test_template_for_every_symbol(size):
    pytest.importorskip("PySide6")
    from gui.draw_mode.template import TemplateProvider
    tp = TemplateProvider()
    assert tp.error == ""
    g = CellGeometry(size=size)
    for code in ALL_CODES:
        s = tp.shape(code, g)
        assert s is not None, chr(code)
        r = s.rect
        assert r.left() >= 0 and r.right() <= g.width and r.top() >= 0 and r.bottom() <= g.height, chr(code)
        assert abs(r.center().x() - g.cx) < 1.0, chr(code)       # по центру клетки
    tol = 0.03 * g.cap
    for ch in "нхHx5ЕE":                                         # стоят на базовой линии
        assert abs(tp.shape(ord(ch), g).rect.bottom() - g.baseline) < tol, ch
    for ch in "нхxzw":                                           # строчные — до линии строчных
        assert abs(tp.shape(ord(ch), g).rect.top() - g.xline) < tol, ch
    for ch in "НHЕE":                                            # заглавные — до линии заглавных
        assert abs(tp.shape(ord(ch), g).rect.top() - g.capline) < tol, ch
    assert tp.shape(ord("р"), g).rect.bottom() > g.baseline + 0.2 * g.cap   # нижний выносной
    assert tp.shape(ord("б"), g).rect.top() < g.xline - 0.2 * g.cap         # верхний выносной
    o, O = tp.shape(ord("о"), g).rect, tp.shape(ord("О"), g).rect
    assert o.height() < 0.85 * O.height()                                  # «о» не как «О»
    comma = tp.shape(ord(","), g).rect
    assert comma.top() > g.xline and comma.bottom() > g.baseline           # запятая у базовой линии
    dash = tp.shape(ord("-"), g).rect
    assert g.xline < dash.center().y() < g.baseline


def test_template_box_and_gfont_hint(tmp_path):
    pytest.importorskip("PySide6")
    from gui.draw_mode.template import TemplateProvider
    tp = TemplateProvider()
    g = CellGeometry()
    assert tp.shape(ord(" "), g) is None
    # символа нет в образце -> пунктирная рамка с подписью
    tp._src.cmap.pop(ord("№"), None)
    tp.clear_cache()
    s = tp.shape(ord("№"), g)
    assert s.kind == "box" and s.label == "№"
    assert abs(s.rect.bottom() - g.baseline) < 1e-6
    # свой шаблон .gfont: подсказка — его штрихи
    pr = sample_project()
    out = tmp_path / "hint.gfont"
    export_project(pr, ExportOptions(str(out)))
    tp.set_gfont(str(out))
    s = tp.shape(ord("Н"), g)
    assert s.kind == "strokes"
    assert abs(s.rect.bottom() - g.baseline) < 0.05 * g.cap


def test_order_hint():
    pytest.importorskip("PySide6")
    from gui.draw_mode.template import TemplateProvider
    tp = TemplateProvider()
    g = CellGeometry()
    h = tp.hint(ord("й"), g)
    assert h is not None and len(h.lines) == 2
    assert h.lines[1][:, 1].max() < h.lines[0][:, 1].min()    # дужка — последней, над буквой


# ------------------------------------------------------------ GUI
def test_draw_mode_gui_smoke(tmp_path):
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from gui.selftest import SMOKE_DRAW_CHARS, run_draw_smoke
    code = run_draw_smoke(str(tmp_path))
    report = (tmp_path / "smoke_draw.txt").read_text(encoding="utf-8")
    assert code == 0, report
    for ch in SMOKE_DRAW_CHARS:
        assert (tmp_path / f"canvas_template_U+{ord(ch):04X}.png").stat().st_size > 5000
    assert (tmp_path / "preview_line.png").stat().st_size > 5000
