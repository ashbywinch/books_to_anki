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

    cumulative_chars = current_sentence_base = 0
    with open(inputfile, mode="r", encoding="utf-8") as file:
        for line in file:
            docs = nlp.pipe([line.strip()])

            prev_span: Span = None
            for doc in docs:
                for s in doc.sents:
                    for span in split_sentence(doc, s, max_span_length=maxfieldlen):
                        yield Card(
                            inputfile,
                            current_sentence_base + span.start_char,
                            "",
                            span.text,
                            "",
                            "",
                        )
                        if (
                            prev_span and span.doc is not prev_span.doc
                        ):  # once current_span moves from one line to the next
                            current_sentence_base = cumulative_chars
                        prev_span = span

                break  # there was only one doc, hopefully!
            # how many chars to start of current line?
            cumulative_chars = cumulative_chars + len(line.strip())
