"""Tests for book_complexity module"""

import unittest

from book_complexity import book_complexity
from book_complexity.book_complexity import make_nlp


class TestBookComplexity(unittest.TestCase):
    """Tests for book_complexity module"""

    nlp = make_nlp("ru_core_news_sm")

    def test_simple_sentence(self):
        """Are complexity calcs correct on a known short string?"""
        teststrings = [
            """Дедушка поцеловал Лидиньку""",
        ]
        complexity = book_complexity(teststrings, self.nlp)
        self.assertEqual(complexity.mean_grammar_depth, 2)
        self.assertEqual(complexity.mean_words_per_sentence, 3)
        self.assertEqual(complexity.mean_word_length, 8)
        self.assertEqual(complexity.word_count, 3)
        self.assertEqual(complexity.overall_score, 2*3*8)

    def test_multiple_lines(self):
        """Are complexity calcs correct for multiple longer strings?"""
        teststrings = [
            """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль 
            и попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
            """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку""",
        ]

        complexity = book_complexity(teststrings, self.nlp)
        self.assertEqual(complexity.word_count, 52)
        self.assertEqual(complexity.mean_words_per_sentence, 26)
        self.assertEqual(complexity.mean_word_length, 5)
        self.assertEqual(complexity.mean_grammar_depth, 6.5)


if __name__ == "__main__":
    unittest.main()
