"""Мост для Android (android_api.py): те же сценарии, что выполняет Kotlin-интерфейс."""

import json

import numpy as np
import pytest

import android_api as A
from gfont.session import resource_dir


class Progress:
    def __init__(self, cancel_after=None):
        self.calls = []
        self.cancel_after = cancel_after

    def onProgress(self, d, t):
        self.calls.append((d, t))

    def isCancelled(self):
        return self.cancel_after is not None and len(self.calls) >= self.cancel_after


def J(s):
    d = json.loads(s)
    assert d["ok"], d
    return d


@pytest.fixture(autouse=True)
def fresh(tmp_path):
    A._debug_reset()
    J(A.init(str(tmp_path / "files"), str(resource_dir())))
    yield
    A._debug_reset()


def test_converter_flow(tmp_path, test_font):
    pres = J(A.conv_presets())
    assert ["ru_en", "Русский + английский + цифры + знаки"] in pres["presets"]
    assert json.loads(A.conv_preview("а", "{}"))["ok"] is False          # шрифт не открыт
    f = J(A.conv_open_font(test_font))
    assert f["glyphs"] > 100
    cov = J(A.conv_coverage(json.dumps({"charset_preset": "ru"})))
    assert cov["have"] == cov["total"] == 66
    pv = J(A.conv_preview("Аб в", json.dumps({"slant": 10})))
    assert set(pv["glyphs"]) == {"А", "б", "в"} and pv["glyphs"]["б"]
    out = tmp_path / "папка с пробелом" / "шрифт.gfont"
    prog = Progress()
    r = J(A.conv_save(str(out), json.dumps({"charset_preset": "ru"}), "", prog))
    assert r["valid"] and out.exists() and prog.calls
    assert J(A.validate(str(out)))["valid"]


def test_converter_cancel(tmp_path, test_font):
    J(A.conv_open_font(test_font))
    r = json.loads(A.conv_save(str(tmp_path / "x.gfont"), "{}", "", Progress(cancel_after=3)))
    assert r["ok"] is False and r.get("cancelled")
    assert not (tmp_path / "x.gfont").exists()


def _line(a, b, n=30):
    t = np.linspace(0, 1, n)[:, None]
    return (np.asarray(a) + (np.asarray(b) - np.asarray(a)) * t).tolist()


def test_draw_flow(tmp_path):
    st = J(A.draw_init())
    assert st["restored"] is False and st["counts"][0] == 0
    geo = J(A.draw_geometry())
    guides = dict(geo["guides"])
    cx = geo["width"] / 2
    groups = J(A.draw_groups())["groups"]
    assert groups[0][0] == "Строчные русские" and len(groups) == 7
    tpl = J(A.draw_template(ord("н")))
    assert tpl["kind"] == "outline" and tpl["polys"]
    assert abs(tpl["rect"][1] + tpl["rect"][3] - guides["base"]) < 10
    assert J(A.draw_template(ord(" ")))["kind"] == "none"
    hint = J(A.draw_hint(ord("й")))
    assert len(hint["lines"]) == 2

    J(A.draw_select(ord("н"), 0))
    g = J(A.draw_add_stroke(json.dumps(_line((cx - 80, guides["x"]), (cx - 80, guides["base"]))), False))
    g = J(A.draw_add_stroke(json.dumps(_line((cx + 80, guides["x"]), (cx + 80, guides["base"]))), False))
    g = J(A.draw_add_stroke(json.dumps(_line((cx - 80, guides["base"] - 100), (cx + 80, guides["base"] - 100))), False))
    assert len(g["strokes"]) == 3 and g["status"] == "drawn" and g["can_undo"]
    g = J(A.draw_edit("undo"))
    assert len(g["strokes"]) == 2 and g["can_redo"]
    g = J(A.draw_edit("redo"))
    assert len(g["strokes"]) == 3
    g = J(A.draw_edit("begin_point", 0))
    g = J(A.draw_edit("move_point", 0, 0, cx - 120, guides["x"] - 10))
    assert abs(g["strokes"][0][0][0] - (cx - 120)) < 0.2
    g = J(A.draw_edit("delete_stroke", 2))
    assert len(g["strokes"]) == 2
    # точка
    J(A.draw_select(ord("."), 0))
    g = J(A.draw_add_stroke(json.dumps([[cx, guides["base"] - 5]]), True))
    assert g["dots"] == [True] and len(g["strokes"][0]) == 6
    # варианты
    J(A.draw_select(ord("н"), 1))
    g = J(A.draw_add_stroke(json.dumps(_line((cx - 60, guides["x"]), (cx - 60, guides["base"]))), False))
    assert g["variant"] == 1 and g["nvariants"] == 2
    J(A.draw_select(ord("е"), 0))
    J(A.draw_add_stroke(json.dumps(_line((cx - 70, guides["base"] - 90), (cx + 70, guides["base"] - 90))), False))
    J(A.draw_skip(ord("щ")))
    st = J(A.draw_state())
    assert st["statuses"][str(ord("щ"))][0] == "skipped" and st["counts"][0] == 3

    thumbs = J(A.draw_thumbs(json.dumps([ord("н"), ord("а")])))["glyphs"]
    assert thumbs[str(ord("н"))] and thumbs[str(ord("а"))] is None
    line = J(A.draw_line("не на"))
    assert line["glyphs"]["н"] and line["glyphs"]["а"] is None

    sim = J(A.draw_fill_similar())["candidates"]
    assert str(ord("ё")) in sim and str(ord("e")) in sim
    st = J(A.draw_apply(json.dumps([ord("ё")])))
    assert st["counts"][1] == 1

    st = J(A.draw_settings(json.dumps({"smoothing": 0.8, "size": 1.1, "show_order": True})))
    assert st["settings"]["size"] == pytest.approx(1.1) and st["settings"]["show_order"]

    out = tmp_path / "мой почерк.gfont"
    prog = Progress()
    r = J(A.draw_export(str(out), json.dumps({"remove_old": True}), prog))
    assert r["valid"] and r["by_user"] == 3 and r["auto"] == 1, r["text"]
    assert J(A.validate(str(out)))["valid"]

    # проект: сохранить, открыть, черновик
    proj = tmp_path / "проект.gfproj"
    J(A.draw_save(str(proj)))
    J(A.draw_autosave())
    A._debug_reset()
    st = J(A.draw_init())
    assert st["restored"] and st["counts"][:2] == [3, 1]
    J(A.draw_new())
    assert J(A.draw_state())["counts"][0] == 0
    st = J(A.draw_open(str(proj)))
    assert st["counts"][:2] == [3, 1]
    # открыть .gfont в редакторе
    J(A.draw_new())
    st = J(A.draw_import_gfont(str(out)))
    assert st["imported"] == 4 and st["settings"]["template"] == str(out)


def test_draw_fill_font_and_sample(tmp_path, test_font):
    J(A.draw_init())
    prog = Progress()
    c = J(A.draw_fill_font(test_font, False, prog))["candidates"]
    assert len(c) > 150 and prog.calls
    st = J(A.draw_apply(json.dumps([int(k) for k in list(c)[:10]])))
    assert st["counts"][1] == 10
    assert J(A.draw_sample(test_font))["sample"]
    assert J(A.draw_template(ord("ж")))["kind"] == "outline"
    bad = json.loads(A.draw_sample(str(tmp_path / "нет.ttf")))
    assert bad["ok"] is False
    assert J(A.draw_sample(""))["sample"] == "DejaVu Sans"
