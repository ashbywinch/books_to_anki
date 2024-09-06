import glob
from pathlib import Path
from book_to_flashcards.Card import Card
from split_sentences import make_nlp, split_text


from collections.abc import Generator
from typing import Any

def cards_untranslated_from_folder(
    inputfolder, pipeline, maxfieldlen
) -> Generator[Card, Any, Any]:
    for filename in glob.glob(inputfolder + "/**/*.txt", recursive=True):
        yield from cards_untranslated_from_file(
            inputfile=filename, pipeline=pipeline, maxfieldlen=maxfieldlen
        )

def cards_untranslated_from_file(
    inputfile, pipeline, maxfieldlen
) -> Generator[Card, Any, Any]:
    """Take a single text file and produce a set of flash cards
    containing chunks not longer than maxfieldlen, with no translations included
    (so, just the front)
    This is much quicker and avoids 'using up' a DeepL API key if you don't need it"""
    nlp = make_nlp(pipeline)

    file = open(inputfile, mode="r", encoding="utf-8")
    docs = nlp.pipe(file)

    for span in split_text(docs, max_span_length=maxfieldlen):
        yield Card(
            filename = Path(inputfile).as_posix(),
            index_in_file= span.start,
            text = span.text_with_ws,
        )