"""Tests for book_complexity module"""

from collections.abc import Generator
import unittest

from book_complexity import make_nlp
from book_complexity.ComplexityCalculators import (
    CumulativeGrammarDepthComplexityCalculator,
    CumulativeWordLengthComplexityCalculator,
    SentenceCountComplexityCalculator,
    VocabularyLevelComplexityCalculator,
    WordCountComplexityCalculator,
    WordsKnownComplexityCalculator,
)
from spacy.tokens import Doc


class TestBookComplexity(unittest.TestCase):
    """Tests for book_complexity module"""

    nlp = make_nlp("ru_core_news_sm")

    # let's not explode when we see non-Latin-1 text
    short_string = "Дедушка поцеловал Лидиньку"

    long_strings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль 
            и попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку""",
    ]

    def short_doc(self) -> Doc:
        return next(self.nlp.pipe([self.short_string]))

    def longer_docs(self) -> Generator[Doc]:
        return self.nlp.pipe(self.long_strings)

    def test_grammar_depth_simple(self):
        """Are complexity calcs correct on a known short string?"""
        calculator = CumulativeGrammarDepthComplexityCalculator()
        calculator.read(self.short_doc())
        self.assertEqual(calculator.value(), 2)

    def test_word_count_simple(self):
        """Are word count calcs correct on a known short string?"""
        calculator = WordCountComplexityCalculator()
        calculator.read(self.short_doc())
        self.assertEqual(calculator.value(), 3)

    def test_sentence_count_simple(self):
        """Are sentence count calcs correct on a known short string?"""
        calculator = SentenceCountComplexityCalculator()
        calculator.read(self.short_doc())
        self.assertEqual(calculator.value(), 1)

        # self.assertEqual(complexity.mean_words_per_sentence, 3)
        # self.assertEqual(complexity.mean_word_length, 8)

    def test_word_count_long(self):
        """Are word count calcs correct for multiple longer strings?"""

        calculator = WordCountComplexityCalculator()
        for doc in self.longer_docs():
            calculator.read(doc)
        self.assertEqual(calculator.value(), 52)

    def test_sentence_count_long(self):
        """Are word count calcs correct for multiple longer strings?"""

        calculator = SentenceCountComplexityCalculator()
        for doc in self.longer_docs():
            calculator.read(doc)
        self.assertEqual(calculator.value(), 2)

    def test_cumulative_grammar_depth_long(self):
        """Are grammar depth calcs correct for multiple longer strings?"""

        calculator = CumulativeGrammarDepthComplexityCalculator()
        for doc in self.longer_docs():
            calculator.read(doc)
        self.assertEqual(calculator.value(), 13)

    def test_cumulative_word_length_long(self):
        """Are word length calcs correct for multiple longer strings?"""
        calculator = CumulativeWordLengthComplexityCalculator()
        for doc in self.longer_docs():
            calculator.read(doc)
        self.assertEqual(calculator.value(), 277)
        # not the same as total string length, since the calculation ignores punctuation

    def test_known_words(self):
        teststrings = ["Bob likes green peas"]
        vocabulary = {"likes", "peas"}
        doc = next(self.nlp.pipe(teststrings))
        calculator = WordsKnownComplexityCalculator(vocabulary)
        calculator.read(doc)

        self.assertEqual(calculator.value(), 2)

    def test_vocabulary_level(self):
        frequency = {"peas": 500, "likes": 20}
        levels = [range(0, 400), range(400, 1000)]
        teststrings = ["Bob likes green peas"]

        doc = next(self.nlp.pipe(teststrings))
        calculator = VocabularyLevelComplexityCalculator(frequency, levels)
        calculator.read(doc)

        self.assertEqual(calculator.value(), 1)


if __name__ == "__main__":
    unittest.main()
