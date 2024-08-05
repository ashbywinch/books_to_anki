from book_to_flashcards.Card import Card
from split_sentences import make_nlp, split_sentence


from collections.abc import Generator
from typing import Any


def cards_untranslated_from_file(
    inputfile, pipeline, maxfieldlen
) -> Generator[Card, Any, Any]:
    """Take a single text file and produce a set of flash cards
    containing chunks not longer than maxfieldlen, with no translations included
    (so, just the front)
    This is much quicker and avoids 'using up' a DeepL API key if you don't need it"""
    nlp = make_nlp(pipeline)

    prev_span = current_span = None
    cumulative_chars = current_sentence_base = 0
    with open(inputfile, mode="r", encoding="utf-8") as file:
        for line in file:
            docs = nlp.pipe([line.strip()])

            for doc in docs:
                for s in doc.sents:
                    for next_span in split_sentence(
                        doc, s, max_span_length=maxfieldlen
                    ):
                        if current_span:
                            yield Card(
                                inputfile,
                                current_sentence_base + current_span.start_char,
                                prev_span.text if prev_span else "",
                                current_span.text,
                                next_span.text,
                                "",
                            )
                        prev_span = current_span
                        current_span = next_span
                        if (
                            prev_span and current_span.doc is not prev_span.doc
                        ):  # once current_span moves from one line to the next
                            current_sentence_base = cumulative_chars

                break  # there was only one doc, hopefully!
            # how many chars to start of current line?
            cumulative_chars = cumulative_chars + len(line.strip())

        yield Card(
            inputfile,
            cumulative_chars + current_span.start_char,
            prev_span.text if prev_span else None,
            current_span.text,
            "",
            "",
        )
