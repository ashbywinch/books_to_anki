"""Test split sentences module"""

import pytest
from split_sentences import consolidate_spans, make_nlp, split_sentence


@pytest.fixture()
def nlp_ru():
    yield make_nlp("ru_core_news_sm")


class TestSentenceSplitting:
    """Test split_sentences module"""

    teststrings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль и 
        попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
        слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
        когда маменька им показывает книжку""",
    ]
    max_chars = 70

    def get_sents(self, nlp_ru):
        for s in self.teststrings:
            docs = nlp_ru.pipe([s])
            for doc in docs:
                for sent in doc.sents:
                    yield (doc, sent)

    def test_max_chars(self, nlp_ru):
        """Do we respect the max_char limit?"""
        for doc, sent in self.get_sents(nlp_ru):
            for span in split_sentence(doc, sent, max_span_length=self.max_chars):
                assert len(span.text) <= self.max_chars

    def test_all_text_present(self, nlp_ru):
        """If we split a document, and then concatenate it all together again, is it the same?"""
        for doc, sent in self.get_sents(nlp_ru):
            spans = split_sentence(doc, sent, max_span_length=self.max_chars)
            span = consolidate_spans(doc, spans, None)[0]
            assert sent.text == span.text
