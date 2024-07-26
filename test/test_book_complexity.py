"""Tests for book_complexity module"""

import unittest

from book_complexity import book_complexity, make_nlp
from book_complexity.ComplexityCalculators import (
    cumulative_grammar_depth,
    sentence_count,
    word_count,
)


nlp = make_nlp("ru_core_news_sm")


class TestBookComplexityOnShortString(unittest.TestCase):
    """Tests for book_complexity module"""

    # let's not explode when we see non-Latin-1 text
    short_string = "Дедушка поцеловал Лидиньку"
    doc = next(nlp.pipe([short_string]))

    def test_grammar_depth_simple(self):
        """Are grammar depth correct on a known short string?"""
        self.assertEqual(cumulative_grammar_depth(self.doc), 2)

    def test_word_count_simple(self):
        """Are word count calcs correct on a known short string?"""
        self.assertEqual(word_count(self.doc), 3)

    def test_sentence_count_simple(self):
        """Are sentence count calcs correct on a known short string?"""
        self.assertEqual(sentence_count(self.doc), 1)


class TestBookComplexityOnMultipleLongerStrings(unittest.TestCase):
    long_strings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль 
            и попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку""",
    ]

    def setUp(self):
        self.complexity = book_complexity(self.long_strings, nlp)

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
        complexity = book_complexity(teststrings, nlp, vocabulary=vocabulary)

        self.assertEqual(complexity["Words Known"], 2)
        self.assertEqual(complexity["Percent Words Known"], 50)

    def test_vocabulary_level(self):
        frequency = {"peas": 500, "likes": 20}
        levels = [range(0, 400), range(400, 1000)]
        teststrings = ["Bob likes green peas"]

        complexity = book_complexity(
            teststrings, nlp, frequency=frequency, levels=levels
        )

        self.assertEqual(complexity["Vocabulary Level"], 1)


if __name__ == "__main__":
    unittest.main()
