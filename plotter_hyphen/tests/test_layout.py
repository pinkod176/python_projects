from hyph.layout import wrap_text


def mono(s):
    """Каждый символ — 1 единица."""
    return float(len(s))


def test_rightmost_break_that_fits():
    # "Тест " (5) + "программи-" (10) = 15
    r = wrap_text("Тест программирование", mono, 15)
    assert r.lines == ["Тест программи-", "рование"]
    assert r.hyphens == 1
    r = wrap_text("Тест программирование", mono, 13)
    assert r.lines == ["Тест програм-", "мирование"]


def test_hyphen_width_is_counted():
    # «Тест программи» без дефиса занимает ровно 14, но с дефисом уже 15 — не влезает.
    r = wrap_text("Тест программирование", mono, 14)
    assert r.lines == ["Тест програм-", "мирование"]

    def wide_dash(s):
        return sum(5.0 if c == "-" else 1.0 for c in s)
    # «Тест програм-» = 5 + 7 + 5 = 17 > 15, «Тест про-» = 13 — подходит.
    r = wrap_text("Тест программирование", wide_dash, 15)
    assert r.lines == ["Тест про-", "граммирование"]


def test_whole_word_when_no_break_fits():
    # Самая короткая левая часть «ав-» не помещается — слово целиком на новую строку.
    r = wrap_text("Тест автор", mono, 7)
    assert r.lines == ["Тест", "автор"]
    assert r.hyphens == 0


def test_not_hyphenated_tokens_move_whole():
    for word in ["1234567", "ООО", "iPhone", "кот"]:
        r = wrap_text("Тест " + word, mono, 7)
        assert r.lines == ["Тест", word], word


def test_hyphen_word_split_at_its_dash():
    r = wrap_text("Тест кто-то", mono, 9)
    assert r.lines == ["Тест кто-", "то"]


def test_punctuation_goes_with_word():
    r = wrap_text("Тест объявление, дальше", mono, 11)
    assert r.lines == ["Тест объяв-", "ление,", "дальше"]
    r = wrap_text("Тест объявление, дальше", mono, 12)
    assert r.lines == ["Тест объяв-", "ление, даль-", "ше"]
    r = wrap_text("Тест «объявление»", mono, 11)
    assert r.lines == ["Тест «объ-", "явление»"]
    for line in r.lines[1:]:
        assert line[0].isalpha() or line[0] in "«(", line


def test_off_is_old_behaviour():
    text = "Программирование плоттера — интересное занятие для всех"
    r = wrap_text(text, mono, 20, hyphenate=False)
    assert all("-" not in line for line in r.lines)
    assert " ".join(r.lines) == text
    assert all(len(line) <= 20 for line in r.lines)


def test_long_word_split_several_times():
    r = wrap_text("программирование", mono, 7)
    assert r.lines == ["про-", "грамми-", "рование"]
    assert "".join(l[:-1] if l.endswith("-") else l for l in r.lines) == "программирование"
    assert r.overflow == []


def test_overflow_reported_for_unbreakable_long_word():
    r = wrap_text("Тест 12345678901234567890", mono, 10)
    assert r.lines == ["Тест", "12345678901234567890"]
    assert r.overflow == [1]


def test_paragraphs_and_indent_preserved():
    text = "Первый абзац.\n\n    Второй абзац с отступом"
    r = wrap_text(text, mono, 100)
    assert r.text == text
    r = wrap_text("а б\r\nв", mono, 100)
    assert r.lines == ["а б", "в"]


def test_no_line_starts_with_space_or_punctuation():
    text = ("Программирование плоттера, объявление: подъезд, чайка; классный (кто-то) "
            "обезьяна! Автор? «Сверхъестественный» результат.")
    for width in range(8, 40):
        r = wrap_text(text, mono, width)
        for line in r.lines:
            assert line == line.strip()
            assert line[:1].isalpha() or line[:1] in "«(", (width, line)
        # Склеенный обратно текст совпадает с исходным.
        joined = ""
        for line in r.lines:
            if joined.endswith("-") and line[:1].isalpha():
                piece = joined[:-1]
                # дефис из слова «кто-то» не убираем
                joined = joined if joined.endswith("кто-") else piece
                joined += line
            else:
                joined += (" " if joined else "") + line
        assert joined == text, width
