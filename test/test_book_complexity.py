from book_complexity import *
import unittest

from book_complexity.book_complexity import make_nlp

class TestBookComplexity(unittest.TestCase):
    def test_simple_sentence(self):
        teststrings = [
            """Дедушка поцеловал Лидиньку""",
        ]
        nlp = make_nlp("ru_core_news_sm")
        complexity = book_complexity(teststrings, nlp)
        self.assertEqual(complexity.mean_grammar_depth, 2)
        self.assertEqual(complexity.mean_words_per_sentence, 3)
        self.assertEqual(complexity.mean_word_length, 8)
        self.assertEqual(complexity.word_count, 3)

    def test_multiple_lines(self):
        teststrings = [
            """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль 
            и попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
            """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку"""
        ]
        nlp = make_nlp("ru_core_news_sm")
        complexity = book_complexity(teststrings, nlp)
        self.assertEqual(complexity.word_count, 52)
        self.assertEqual(complexity.mean_words_per_sentence, 26)
        self.assertEqual(complexity.mean_word_length, 5)
        self.assertEqual(complexity.mean_grammar_depth, 2.1)


if __name__ == '__main__':    unittest.main()
