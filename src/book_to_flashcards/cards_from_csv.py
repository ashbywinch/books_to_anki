from collections.abc import Generator
from typing import Any
from unicodecsv import UnicodeReader

from book_to_flashcards.Card import Card


def cards_from_csv(inputfile: str) -> Generator[Card, Any, Any]:
    with open(inputfile, mode="rb") as input:
        csvreader = UnicodeReader(input)
        for filename, index_in_file, prev, current, next, translation in csvreader:
            yield Card(filename, index_in_file, prev, current, next, translation)
