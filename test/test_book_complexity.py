"""Tests for book_complexity module"""

import glob
import unittest

from book_complexity import get_book_complexity, make_nlp
from book_complexity.ComplexityCalculators import (
    sentence_grammar_depth,
    sentence_count,
)
from book_complexity.book_complexity import get_complexities

nlp_ru = make_nlp("ru_core_news_sm")
nlp_en = make_nlp("en_core_web_sm")


class TestBookComplexityOnShortString(unittest.TestCase):
    """Tests for book_complexity module"""

    # let's not explode when we see non-Latin-1 text
    short_string = "Дедушка поцеловал Лидиньку"
    doc = next(nlp_ru.pipe([short_string]))

    def test_grammar_depth_simple(self):
        """Are grammar depth correct on a known short string?"""
        self.assertEqual(sentence_grammar_depth(next(self.doc.sents)), 2)

    def test_sentence_count_simple(self):
        """Are sentence count calcs correct on a known short string?"""
        self.assertEqual(sentence_count(next(self.doc.sents)), 1)


class TestBookComplexityOnMultipleLongerStrings(unittest.TestCase):
    long_strings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль 
            и попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку""",
    ]

    def setUp(self):
        self.complexity = get_book_complexity(self.long_strings, nlp_ru)

    def test_word_count_long(self):
        self.assertEqual(self.complexity["Word Count"], 52)

    def test_sentence_count_long(self):
        self.assertEqual(self.complexity["Sentence Count"], 2)

    def test_mean_grammar_depth_long(self):
        self.assertEqual(self.complexity["Mean Grammar Depth"], 6.5)

    def test_mean_word_length_long(self):
        self.assertEqual(self.complexity["Mean Word Length"], 5.3)

    def test_known_words(self):
        teststrings = ["Bob likes green peas"]
        vocabulary = {"likes", "peas"}
        complexity = get_book_complexity(teststrings, nlp_en, vocabulary=vocabulary)

        self.assertEqual(complexity["Words Known"], 2)
        self.assertEqual(complexity["Percent Words Known"], 50)

    def test_vocabulary_level(self):
        frequency = {"peas": 500, "likes": 20}
        levels = [range(0, 400), range(400, 1000)]
        teststrings = ["Bob likes green peas"]

        complexity = get_book_complexity(
            teststrings, nlp_en, frequency=frequency, levels=levels
        )

        self.assertEqual(complexity["Vocabulary Level"], 1)


class test_get_complexities_from_folder(unittest.TestCase):
    def test_complexities(self):
        files = glob.glob("test/data/dummy_books/**/*.txt", recursive=True)
        complexities = list(get_complexities(files, nlp=nlp_en))
        self.assertEqual(len(list(complexities)), 2)
        self.assertEqual(complexities[0]["title"], "dummy_book")
        self.assertEqual(complexities[0]["author"], "dummy_books")
        self.assertEqual(complexities[0]["lang"], "en")


if __name__ == "__main__":
    unittest.main()
