"""Порядок и направление штрихов «как при письме рукой»."""

import numpy as np
import pytest

from gfont.session import FontSession, UiParams
from gfont.stroke_order import hand_order, orient_closed, orient_open


def _area(q):
    x, y = np.asarray(q)[:-1, 0], np.asarray(q)[:-1, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def test_open_strokes_direction():
    v = np.array([[0, 100.0], [0, -100.0]])          # снизу вверх -> развернуть
    assert orient_open(v)[0][1] == -100.0
    h = np.array([[100.0, 0], [-100.0, 0]])          # справа налево -> развернуть
    assert orient_open(h)[0][0] == -100.0


def test_closed_loop_counterclockwise_from_top():
    t = np.linspace(0, 2 * np.pi, 40)
    ring = np.stack([100 * np.cos(t), 100 * np.sin(t)], axis=1)   # по часовой на экране (Y вниз)
    q = orient_closed(ring)
    assert np.allclose(q[0], q[-1])
    assert _area(q) < 0                              # против часовой на экране
    assert q[0][1] < -80                             # начало вверху


def test_marks_last_and_bars_after_stems():
    stem_l = np.array([[-100, -300.0], [-100, 0.0]])
    stem_r = np.array([[100, -300.0], [100, 0.0]])
    bar = np.array([[100, -150.0], [-100, -150.0]])  # справа налево
    dot = np.array([[0, -380.0], [5, -385.0], [0, -390.0], [-5, -385.0]])
    out = hand_order([bar, stem_r, dot, stem_l], [False, False, True, False],
                     letter=True, cap=315)
    assert out[0][0][0] == -100 and out[1][0][0] == 100   # стойки слева направо
    assert out[2][0][0] == -100                           # перекладина слева направо
    assert out[3][0][1] <= -380                           # точка последней


@pytest.fixture
def session(test_font):
    return FontSession(test_font)


def _strokes(session, ch, **kw):
    return [np.array(s) for s in session.glyph(ord(ch), UiParams(**kw)).strokes]


def test_font_letters(session):
    o = _strokes(session, "о")
    assert len(o) == 1 and _area(o[0]) < 0               # «о» против часовой
    assert o[0][0][1] < o[0][:, 1].min() + 0.2 * np.ptp(o[0][:, 1])   # от верха

    h = _strokes(session, "Н")
    assert len(h) == 3
    assert h[0][:, 0].mean() < h[1][:, 0].mean()         # левая стойка, затем правая
    bar = h[2]
    assert abs(bar[-1][1] - bar[0][1]) < 0.35 * abs(bar[-1][0] - bar[0][0])
    assert bar[0][0] < bar[-1][0]                        # перекладина последней, слева направо

    yo = _strokes(session, "ё")
    main_top = yo[0][:, 1].min()
    assert all(s[:, 1].max() < main_top for s in yo[-2:])   # две точки — последними

    short_i = _strokes(session, "й")
    assert short_i[-1][:, 1].max() < short_i[0][:, 1].min()  # кратка последней

    l = _strokes(session, "л")
    assert l[0][0][0] == min(p[0] for s in l for p in s)     # «л» начинается слева (снизу)


def test_hand_order_can_be_disabled(session):
    assert _strokes(session, "й", hand_order=False)
