"""Смоук-тест GUI (offscreen): окно, загрузка шрифта, предпросмотр, сохранение, проверка."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_gui_smoke(tmp_path, test_font):
    from gui.selftest import run_gui_smoke
    code = run_gui_smoke(test_font, str(tmp_path))
    report = (tmp_path / "smoke.txt").read_text(encoding="utf-8")
    assert code == 0, report
    assert "RESULT: OK" in report
    for name in ("screen_preview.png", "screen_glyphs.png", "screen_saved.png"):
        assert (tmp_path / name).stat().st_size > 10000


def test_engine_selftest(tmp_path, test_font):
    from gui.selftest import run_engine_selftest
    code = run_engine_selftest(test_font, str(tmp_path))
    assert code == 0, (tmp_path / "selftest.txt").read_text(encoding="utf-8")
