import glob
from pathlib import Path
from book_to_flashcards.Card import Card
from split_sentences import make_nlp, split_text

from collections.abc import Generator
from typing import Any

def trim_title(title:str, separator:str) -> str:
    return title if separator == "" else separator.join(title.split(separator)[:-1])

def card_trim_title(card:Card, separator:str) -> Card:
    return Card(
        title = trim_title(card.title, separator),
        author=card.author,
        start = card.start,
        end = card.end,
        text = card.text,
        translation = card.translation
    )

# If the first card in a given book has the author name as the text, don't yield it
def cards_skip_first_line_if_author(cards) -> Generator[Card, Any, Any]:
    current_author = ""
    current_title = ""
    for card in cards:
        # If we're the same book as the last card we saw, just yield the card and carry on
        same_book = current_author == card.author and current_title == card.title
        if same_book:
            yield card
        else:
            current_author = card.author
            current_title = card.title

        # This is not the same book as the last card, so it's the first card in a book.
        if not same_book:
            lines = card.text.splitlines()
            if len(lines) > 0:
                if lines[0] == card.author: # we found the author on the first line, now to throw it away!
                    if len(lines) > 1:
                        yield Card(
                            title = card.title,
                            author = card.author,
                            start = card.start + len(card.author) + 1, # 1 for the newline
                            end = card.end,
                            text = "\n".join(lines[1:]), # get rid of that first line
                            translation = card.translation
                        )
                else: # we didn't find it, just pass the card straight through
                    yield card


        

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
            title = Path(inputfile).stem,
            author = Path(inputfile).parent.stem,
            start = span.start,
            end = span.end,
            text = span.text_with_ws,
        )