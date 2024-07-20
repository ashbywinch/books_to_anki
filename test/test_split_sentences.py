from split_sentences import make_nlp, split_sentence, consolidate_spans
import unittest

class TestSentenceSplitting(unittest.TestCase):
    teststrings = [
        "Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль и попросила разменять другой, чтобы снести два гривенника бедному хромому.",
        "Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, когда маменька им показывает книжку"
    ]
    max_chars = 70
    nlp = make_nlp()

    def __test_all_sentences(self, test_fn):
        for s in self.teststrings:
            docs = self.nlp.pipe([s])
            for doc in docs:
                for sent in doc.sents:
                    test_fn(doc, sent)

    def test_max_chars(self):
        self.__test_all_sentences(test_fn = lambda doc,sent: self.__test_max_chars(doc=doc, sent=sent))

    def test_all_text_present(self):
        self.__test_all_sentences(test_fn = lambda doc,sent: self.__test_all_text_present(doc=doc, sent=sent))

    def __test_max_chars(self, doc, sent):
        for span in split_sentence(doc, sent, max_span_length = self.max_chars):
            self.assertLessEqual(len(span.text), self.max_chars, f"text is longer than {self.max_chars} chars")

    def __test_all_text_present(self, doc, sent):
        spans = split_sentence(doc, sent, max_span_length = self.max_chars)
        span = consolidate_spans(doc, spans, None)[0]
        self.assertEqual(sent.text, span.text)

if __name__ == '__main__':
    unittest.main()
