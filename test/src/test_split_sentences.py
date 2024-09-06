"""Test split sentences module"""

import pytest
from split_sentences import consolidate_spans, make_nlp, split_sentence, split_sentences, split_text


@pytest.fixture()
def nlp_ru():
    yield make_nlp("ru_core_news_sm")


class TestSentenceSplitting:
    """Test split_sentences module"""

    # 152 chars. 185 chars. 
    # 187 chars. 
    # Many sentences all shorter than max_chars.
    teststrings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль и попросила разменять другой, чтобы снести два гривенника бедному хромому. Дедушка Ириней любит особенно маленькую Лидиньку, и когда Лидинька умна, дедушка дарит ей куклу, конфетку, а иногда пятачок, гривенник, пятиалтынный, двугривенный, четвертак, полтинник.""", # two sentences in one string
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, когда маменька им показывает книжку.""", # only one sentence
        """Дедушка. поцеловал. Лидиньку, а она. опрометью побежала. к Даше, отдала ей рубль. и попросила разменять другой, чтобы. снести два гривенника бедному хромому"""
    ]
    max_chars = 70

    def get_docs(self, nlp_ru):
        yield from nlp_ru.pipe(self.teststrings)
            
    def get_sents(self, nlp_ru):
        for doc in self.get_docs(nlp_ru):
            for sent in doc.sents:
                yield (doc, sent)

    def test_max_chars(self, nlp_ru):
        """Do we respect the max_char limit?"""
        for doc, sent in self.get_sents(nlp_ru):
            for span in split_sentence(doc, sent, max_span_length=self.max_chars):
                assert len(span.text) <= self.max_chars

    @pytest.mark.parametrize(
        "iSent,expectedSpans",
        [
            [0, 3],
            [1, 4],
            [2, 4],
        ],
    )
    def test_all_text_present(self, nlp_ru, iSent:int, expectedSpans:int):
        """If we split a document, and then concatenate it all together again, is it the same?"""
        (doc, sent) = list(self.get_sents(nlp_ru))[iSent]
        spans = list(split_sentence(doc, sent, max_span_length=self.max_chars))
        assert len(spans) == expectedSpans
        spans = list(consolidate_spans(spans, None))
        assert len(spans) == 1
        assert "".join(s.text for s in spans) == sent.text
        

    @pytest.mark.parametrize(
        "iDoc,expectedSpans",
        [
            [0, 7],
            [1, 4],
            [2, 3], # see that our passage with tiny sentences has them all stuck back together again.
        ],
    )
    def test_multi_sentences_all_text_present(self, nlp_ru, iDoc, expectedSpans):
        """If we split a document, and then concatenate it all together again, is it the same?"""
        doc = list(self.get_docs(nlp_ru))[iDoc]
        spans = list(split_sentences(doc, max_span_length=self.max_chars))
        assert len(spans) == expectedSpans
        assert doc.text == "".join([s.text_with_ws for s in spans ])
        spans = list(consolidate_spans(spans, None))
        assert doc.text == "".join([s.text_with_ws for s in spans ])

    def test_multi_lines_all_text_present(self, nlp_ru):
        """If we split a multi line string (so multiple Doc objects), and then concatenate it all together again, is it the same?"""
        docs = list(self.get_docs(nlp_ru))
        spans = list(split_text(docs, max_span_length=self.max_chars))
        assert len(spans) == 14
        assert "".join([doc.text_with_ws for doc in docs]) == "".join([s.text_with_ws for s in spans ])
        spans = list(consolidate_spans(spans, None))
        assert "".join([doc.text_with_ws for doc in docs]) == "".join([s.text_with_ws for s in spans ])

    def test_short_lines(self, nlp_ru):
        text_with_short_lines = """Любил я нежные слова.
Искал таинственных соцветий.
И, прозревающий едва,
Еще шумел, как в играх дети."""
        docs = list(nlp_ru.pipe([text_with_short_lines]))
        spans = list(split_text(docs, max_span_length=self.max_chars))
        assert len(spans) == 2
        assert "".join([doc.text_with_ws for doc in docs]) == "".join([s.text_with_ws for s in spans ])
        spans = list(consolidate_spans(spans, None))
        assert "".join([doc.text_with_ws for doc in docs]) == "".join([s.text_with_ws for s in spans ])