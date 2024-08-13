from pathlib import Path
from book_to_flashcards.Card import Card
from split_sentences import make_nlp, split_sentence


from collections.abc import Generator
from typing import Any
from spacy.tokens import Span


def cards_untranslated_from_file(
    inputfile, pipeline, maxfieldlen
) -> Generator[Card, Any, Any]:
    """Take a single text file and produce a set of flash cards
    containing chunks not longer than maxfieldlen, with no translations included
    (so, just the front)
    This is much quicker and avoids 'using up' a DeepL API key if you don't need it"""
    nlp = make_nlp(pipeline)

    doc_base = current_sentence_base = 0
    prev_span: Span | None = None
    
    file = open(inputfile, mode="r", encoding="utf-8")
    docs = nlp.pipe(file)

    for doc in docs:
        for s in doc.sents:
            for span in split_sentence(doc, s, max_span_length=maxfieldlen):
                doc_len = span.end_char
                
                yield Card(
                    filename = Path(inputfile).as_posix(),
                    index_in_file= doc_base + s.start_char + span.start_char,
                    text = span.text,
                    translation = ""
                )
                
        doc_base = doc_base + doc_len
