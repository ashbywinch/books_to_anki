from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from unicodecsv import UnicodeWriter

from book_to_flashcards.Progress import Progress  # type: ignore


@dataclass
class Card:
    """Representing a single flash card (or 'Note' in Anki)"""

    filename: str
    index_in_file: int
    prev: str | None
    current: str
    next: str | None
    translation: str | None


def cards_to_csv(cards: Generator[Card, Any, Any], outputfile: str, progress: Progress):
    with open(outputfile, mode="wb") as file:
        writer = UnicodeWriter(file)
        filename = None
        for card in cards:
            writer.writerow(
                [
                    card.filename,
                    card.index_in_file,
                    card.prev,
                    card.current,
                    card.next,
                    card.translation,
                ]
            )
            if card.filename != filename:
                progress()
                filename = card.filename
