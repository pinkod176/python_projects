import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from hyph.gfont import build_gfont  # noqa: E402
from hyph.gui import MainWindow  # noqa: E402
from hyph.settings import Settings  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _font_file(tmp_path, with_dash=True):
    glyphs = {ord(ch): [[(-50, -300), (50, -300), (50, 0)]]
              for ch in "абвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ,."}
    if with_dash:
        glyphs[ord("-")] = [[(-30, -150), (30, -150)]]
    p = tmp_path / "test.gfont"
    p.write_bytes(build_gfont(glyphs))
    return str(p)


def _window(tmp_path, **kw):
    # 1 мм = 1 ед. шрифта: эталон "аа" = 100+0+100 при gap=0 -> 200 мм
    s = Settings(font_path=_font_file(tmp_path, kw.pop("with_dash", True)), line_mm=1000,
                 margin_pct=0, calib_text="аа", calib_mm=200, gap=0, space=100, **kw)
    return MainWindow(settings=s, persist=False)


def test_toggle_hyphenation(app, tmp_path):
    w = _window(tmp_path)
    w.ed_in.setPlainText("Тест программирование")
    w.recompute()
    # Лимит 1000 ед.: "Тест " = 500, + "програм-" (760) не влезает, + "про-" (360) — да
    # "граммирование" = 1300 > 1000 — делится ещё раз: "граммиро-" = 860
    assert w.result.lines == ["Тест про-", "граммиро-", "вание"]
    w.cb_hyph.setChecked(False)
    w.recompute()
    assert w.result.lines == ["Тест", "программирование"]
    assert "переносы выключены" in w.status.text()
    w.cb_hyph.setChecked(True)
    w.recompute()
    assert w.result.lines[0].endswith("-")
    w.preview.repaint()
    w.close()


def test_settings_survive_loading(app, tmp_path):
    w = _window(tmp_path)
    assert (w.s.line_mm, w.s.calib_text, w.s.calib_mm, w.s.space) == (1000, "аа", 200, 100)
    assert w.sp_line.value() == 1000
    w.close()


def test_font_without_dash_disables_added_hyphens(app, tmp_path):
    w = _window(tmp_path, with_dash=False)
    assert "НЕТ" in w.font_info.text()
    w.ed_in.setPlainText("Тест программирование")
    w.recompute()
    assert w.result.lines == ["Тест", "программирование"]
    w.close()


def test_default_on():
    assert Settings().hyphenate is True
