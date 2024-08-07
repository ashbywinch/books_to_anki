from collections.abc import Generator
from typing import Any
from unicodecsv import UnicodeReader, UnicodeWriter

from book_to_flashcards.Card import Card
from book_to_flashcards.Progress import Progress


def cards_from_csv(inputfile: str) -> Generator[Card, Any, Any]:
    with open(inputfile, mode="rb") as input:
        csvreader = UnicodeReader(input)
        for filename, index_in_file, prev, current, next, translation in csvreader:
            yield Card(filename, index_in_file, prev, current, next, translation)


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
