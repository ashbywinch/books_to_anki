"""Tests for book_complexity module"""

from glob import glob

from book_complexity import get_book_complexity, make_nlp
from book_complexity import ComplexityCalculators
from book_complexity.book_complexity import (
    VocabLevelCalculator,
    get_complexities,
)
import pytest


@pytest.fixture()
def ru_nlp():
    yield make_nlp("ru_core_news_sm")


@pytest.fixture()
def en_nlp():
    yield make_nlp("en_core_web_sm")


@pytest.fixture()
def complexity(ru_nlp):
    long_strings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль 
            и попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку""",
    ]
    yield get_book_complexity(long_strings, ru_nlp)


class TestBookComplexityOnMultipleLongerStrings:

    def test_word_count_long(self, complexity):
        assert complexity["Word Count"] == 52

    def test_sentence_count_long(self, complexity):
        assert complexity["Sentence Count"] == 2

    def test_mean_grammar_depth_long(self, complexity):
        assert complexity["Mean Grammar Depth"] == 6.5

    def test_mean_word_length_long(self, complexity):
        assert complexity["Mean Word Length"] == 5.3

    def test_known_words(self, en_nlp):
        teststrings = ["Bob likes green peas"]
        vocabulary = {"likes", "peas"}
        complexity = get_book_complexity(teststrings, en_nlp, vocabulary=vocabulary)

        assert complexity["Words Known"] == 2
        assert complexity["Percent Words Known"] == 50

    def simple_test_vocabulary_level(self):
        frequency = {"peas": 500, "likes": 20}
        levels = [range(0, 400), range(400, 1000)]
        calculators = ComplexityCalculators()
        calculators.add(VocabLevelCalculator(frequency, levels))

        calculators.get_results()

    def test_vocabulary_level_basic(self, en_nlp):
        frequency = {"peas": 500, "likes": 20}
        levels = [range(0, 400), range(400, 1000)]
        teststrings = ["Bob likes green peas"]

        complexity = get_book_complexity(
            teststrings, en_nlp, frequency=frequency, levels=levels
        )

        assert complexity["Vocab Level"] == 1

    def test_vocabulary_level_percentile(self, en_nlp):
        frequency = {"peas": 500, "likes": 20, "supercalifragilistic": 2000}
        levels = [range(0, 400), range(400, 1000), range(1000, 5000)]
        teststrings = ["Bob likes green peas " * 5 + " supercalifragilistic"]

        complexity = get_book_complexity(
            teststrings, en_nlp, frequency=frequency, levels=levels
        )
        # Should still only be 1 despite a low frequency word sneaking in
        assert complexity["Vocab Level"] == 1

    def test_complexities(self, en_nlp):
        files = glob("test/data/dummy_books/**/*.txt", recursive=True)
        complexities = list(get_complexities(files, nlp=en_nlp))
        assert len(list(complexities)) == 2
        assert complexities[0]["title"] == "dummy_book"
        assert complexities[0]["author"] == "dummy_books"
        assert complexities[0]["lang"] == "en"

    def test_grammar_depth_simple(self, ru_nlp):
        """Are grammar depth correct on a known short string?"""

        # let's not explode when we see non-Latin-1 text
        short_string = "Дедушка поцеловал Лидиньку"

        doc = next(ru_nlp.pipe([short_string]))
        assert ComplexityCalculators.sentence_grammar_depth(next(doc.sents)) == 2
