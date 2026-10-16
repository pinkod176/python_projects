import pytest

from hyph.rules import Break, show_breaks, token_breaks

# Примеры из задания: слово -> допустимые места переноса ("|").
EXAMPLES = {
    "программирование": "про|грам|ми|ро|ва|ние",
    "подъезд": "подъ|езд",
    "чайка": "чай|ка",
    "классный": "класс|ный",
    "кто-то": "кто-|то",
    "объявление": "объ|яв|ле|ние",
    "1234567": "1234567",
    "ООО": "ООО",
    "автор": "ав|тор",
    "обезьяна": "обе|зья|на",
}


@pytest.mark.parametrize("word,expected", EXAMPLES.items())
def test_examples(word, expected):
    assert show_breaks(word) == expected


@pytest.mark.parametrize("word,expected", {
    "машина": "ма|ши|на",
    "дорога": "до|ро|га",
    "пальто": "паль|то",
    "касса": "кас|са",
    "подход": "под|ход",
    "разбить": "раз|бить",
    "рассказ": "рас|сказ",
    "воздух": "воз|дух",
    "обедать": "обе|дать",
}.items())
def test_more_words(word, expected):
    assert show_breaks(word) == expected


@pytest.mark.parametrize("word", ["программирование", "объявление", "сверхъестественный",
                                  "подъезд", "чайка", "пальто", "воробьи", "майонез",
                                  "обезьяна", "бойкий", "предъявить", "автор", "обедать"])
def test_general_rules(word):
    for b in token_breaks(word):
        left, right = word[:b.pos], word[b.pos:]
        for part in (left, right):
            assert sum(c.isalpha() for c in part) >= 2, (word, left, right)   # не по одной букве
            assert set(part.lower()) & set("аеёиоуыэюя"), (word, left, right)  # гласная в части
        assert right[0].lower() not in "ьъй", (word, left, right)            # ь ъ й не отрываются


@pytest.mark.parametrize("word", ["кот", "мир", "окно", "из-за", "1234567", "ООО", "МГУ",
                                  "СССР", "iPhone", "Windows", "abc-def", "А4", "2024-й",
                                  "т.е.", "covid-19", "ФСБшник"])
def test_not_hyphenated(word):
    assert token_breaks(word) == []


def test_hyphen_word_keeps_dash_on_top():
    assert token_breaks("кто-то") == [Break(4, hyphen=False)]
    # Составное слово: и по дефису, и по слогам частей.
    assert show_breaks("северо-западный") == "се|ве|ро-|за|пад|ный"
    # Короткая часть после дефиса не дробится.
    assert show_breaks("Москва-река") == "Моск|ва-|река"


def test_punctuation_sticks_to_word():
    assert show_breaks("(программирование),") == "(про|грам|ми|ро|ва|ние),"
    assert show_breaks("«объявление»") == "«объ|яв|ле|ние»"
    assert show_breaks("автор.") == "ав|тор."
    # Никакой перенос не ставит знак препинания в начало новой строки.
    for tok in ["автор,", "«чайка»", "подъезд!", "кто-то?", "(машина)"]:
        for b in token_breaks(tok):
            assert tok[b.pos].isalpha(), (tok, b)


def test_capitalized_word_is_not_abbreviation():
    assert show_breaks("Объявление") == "Объ|яв|ле|ние"
    assert show_breaks("ОБЪЯВЛЕНИЕ") == "ОБЪЯВЛЕНИЕ"
