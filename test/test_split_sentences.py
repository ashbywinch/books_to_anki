"""Test split sentences module"""
import unittest

from split_sentences import consolidate_spans, make_nlp, split_sentence


class TestSentenceSplitting(unittest.TestCase):
    """Test split_sentences module"""

    nlp = make_nlp("ru_core_news_sm")
    teststrings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль и 
        попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
        слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
        когда маменька им показывает книжку""",
    ]
    max_chars = 70

    def __test_all_sentences(self, test_fn):
        """Apply a specified test function to all the test sentences"""
        for s in self.teststrings:
            docs = self.nlp.pipe([s])
            for doc in docs:
                for sent in doc.sents:
                    test_fn(doc, sent)

    def test_max_chars(self):
        """Do we respect the max_char limit?"""
        self.__test_all_sentences(
            test_fn=lambda doc, sent: self.__test_max_chars(doc=doc, sent=sent)
        )

    def test_all_text_present(self):
        """If we split a document, and then concatenate it all together again, is it the same?"""
        self.__test_all_sentences(
            test_fn=lambda doc, sent: self.__test_all_text_present(doc=doc, sent=sent)
        )

    def __test_max_chars(self, doc, sent):
        """Do we respect the max_char limit?"""
        for span in split_sentence(doc, sent, max_span_length=self.max_chars):
            self.assertLessEqual(
                len(span.text),
                self.max_chars,
                f"text is longer than {self.max_chars} chars",
            )

    def __test_all_text_present(self, doc, sent):
        """If we split a document, and then concatenate it all together again, is it the same?"""
        spans = split_sentence(doc, sent, max_span_length=self.max_chars)
        span = consolidate_spans(doc, spans, None)[0]
        self.assertEqual(sent.text, span.text)


if __name__ == "__main__":
    unittest.main()
