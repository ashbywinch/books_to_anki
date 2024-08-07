"""Turn text files containing human language into an Anki flashcard deck
allowing the user to read the book in small chunks 
and test their understanding of the translation"""

from collections.abc import Generator
from dataclasses import dataclass
import hashlib
import html
from pathlib import Path
from typing import Any, Callable

import click
import genanki  # type: ignore
import deepl
import jinja2
from importlib_resources import files

from book_to_flashcards.Card import Card
import book_to_flashcards.resources


@dataclass
class AnkiNote:
    """Representing a single flash card (or 'Note' in Anki)"""

    filename: str
    index_in_file: int
    prev: str | None
    current: str
    next: str | None
    translation: str | None


class BookNote(genanki.Note):
    """Anki will update notes on re-import based on a GUID.
    Make sure the GUID we provide is a good stable representation
    of the card. It should be invariant when the translation changes,
    but it should change when we're looking at a different chunk of book.
    e.g. if the book is reprocessed with a different chunk length."""

    @property
    def guid(self):
        # Hash the filename, the character index of the card text within the file, and the card text.
        # It's possible for multiple cards from a file to have the same text
        return genanki.guid_for(self.fields[0], self.fields[1], self.fields[3])


def make_model(font_size: int) -> genanki.Model:
    """Create the Anki model that we use to represent these book cards"""

    # insert font size into CSS template to create actual CSS
    environment = jinja2.Environment()
    css_template_text = (
        files(book_to_flashcards.resources).joinpath("styling.css.jinja").read_text()
    )
    css_template = environment.from_string(css_template_text)
    css = css_template.render(font_size=font_size)

    return genanki.Model(
        1356306641,
        "Book Snippet",
        fields=[
            {"name": "index_in_file"},
            {"name": "file"},
            {"name": "prev"},
            {"name": "current"},
            {"name": "next"},
            {"name": "translation"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": files(book_to_flashcards.resources)
                .joinpath("front_template.html")
                .read_text(),
                "afmt": files(book_to_flashcards.resources)
                .joinpath("back_template.html")
                .read_text(),
            },
        ],
        css=css,
    )


def make_deckname(filename, structure: bool):
    """Name this Anki deck, either just the filename (without extension)
    or else a nested structure matching the input folder structure"""
    if structure:
        directoryelements = list(Path(filename).parts)[0:-1]  # chop off the filename
        directoryelements.append(Path(filename).stem)
        return "::".join(directoryelements)

    return Path(filename).stem


def add_prev_next(cards: Generator[Card, Any, Any]) -> Generator[AnkiNote, Any, Any]:
    prev_card: Card = None
    current_card: Card = None
    for next_card in cards:
        if current_card:
            yield AnkiNote(
                current_card.filename,
                current_card.index_in_file,
                (
                    prev_card.current
                    if (prev_card and prev_card.filename == current_card.filename)
                    else ""
                ),
                current_card.current,
                next_card.current if (next_card.filename == current_card.filename) else "",
                current_card.translation,
            )
        prev_card = current_card
        current_card = next_card

    if current_card:
        yield AnkiNote(
            current_card.filename,
            current_card.index_in_file,
            prev_card.current if prev_card else "",
            current_card.current,
            "",
            current_card.translation,
        )


def do_nothing():
    pass


def cards_to_anki(
    cards: Generator[Card, Any, Any],
    structure: bool,
    ankifile: str,
    fontsize: int,
    on_file_complete: Callable[[], None] = do_nothing,
):
    """Take a list of text files,
    and turn them all into a single Anki deck.
    Supports use of dummy translator for testing"""
    model = make_model(fontsize)

    decks: list[genanki.Deck] = []
    deck = None
    try:
        for note in add_prev_next(cards):
            # if we've hit a new filename after processing some cards, we need to close the deck
            # and make a new one
            deckname = make_deckname(note.filename, structure)
            if deck is None or deck.name != deckname:
                if deck:
                    decks.append(deck)
                    on_file_complete()
                deck = genanki.Deck(
                    # a reasonably stable ID for this deck - hash the filename
                    int(hashlib.sha1(deckname.encode("utf-8")).hexdigest(), 16)
                    % (2**32),
                    html.escape(deckname),
                )

            note = BookNote(
                model=model,
                fields=[
                    str(note.index_in_file),
                    html.escape(Path(note.filename).stem),
                    html.escape(note.prev),
                    html.escape(note.current),
                    html.escape(note.next),
                    html.escape(note.translation),
                ],
            )
            deck.add_note(note)
        if deck:  # don't forget the last one
            decks.append(deck)
            on_file_complete()

    except deepl.DeepLException as e:
        # this takes a very long time, if it falls over we'd like to have some intermediate results!
        # it can fall over because your DeepL key ran out.
        genanki.Package(decks).write_to_file(ankifile)
        click.echo("Problem with DeepL:")
        click.echo(e)
        if e.http_status_code == 413:
            print("You may have reached the translation limits of your API key")

    genanki.Package(decks).write_to_file(ankifile)
