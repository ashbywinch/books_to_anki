from collections.abc import Generator
from typing import Any
import orjsonl as jsonl

from book_to_flashcards import Card


def cards_to_jsonl(iterator, outputfile, __progress):
    jsonl.save(outputfile, iterator)


def cards_from_jsonl(inputfile) -> Generator[Card, Any, Any]:
    for card in jsonl.stream(inputfile):
        yield Card(**card)  # type: ignore[arg-type]
