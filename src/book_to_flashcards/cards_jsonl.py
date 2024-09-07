from collections.abc import Generator
from glob import glob
import os
from typing import Any
from pathlib import Path
import orjsonl as jsonl

from book_to_flashcards import Card

def cards_to_jsonl_file(
    iterator: Generator[Card, Any, Any], outputfile: str, progress=None
):
    jsonl.save(outputfile, iterator)
    if progress:
        progress()


def cards_to_jsonl_folder(
    iterator: Generator[Card, Any, Any], outputfolder, separator:str = "", progress=None
):
    cardTitle = None
    cardAuthor = None
    file = None
    outputfile: Path = Path()
    try:
        for card in iterator:
            if file is None or card.title != cardTitle or card.author != cardAuthor:
                # We're in a different book and need to switch to a new file
                if file:
                    if progress:
                        progress()
                    file.close()
                    if outputfile.suffixes[-1] == ".tmp":
                        os.replace(outputfile, Path(outputfile.parent, outputfile.stem))
                outputfile = Path(outputfolder, card.author, card.title).with_suffix(".jsonl")
                if Path.exists(outputfile):
                    outputfile = outputfile.with_suffix(outputfile.suffix + ".tmp")
                outputfile.parent.mkdir(exist_ok=True, parents=True)
                file = open(outputfile, mode="wb")
                cardTitle = card.title
                cardAuthor = card.author

            jsonl.append(outputfile, card)
        if file:
            file.close()
            if outputfile.suffixes[-1] == ".tmp":
                os.replace(outputfile, Path(outputfile.parent, outputfile.stem))
    finally:
        if file:
            file.close()
    if progress:
        progress()


def cards_to_jsonl(cards, outputfileorfolder, separator: str="", progress=None):
    path = Path(outputfileorfolder)
    if path.is_file():
        cards_to_jsonl_file(cards, outputfileorfolder, progress)
    else:
        cards_to_jsonl_folder(cards, outputfileorfolder, separator, progress)


def cards_from_jsonl_file(inputfile) -> Generator[Card, Any, Any]:
    for card in jsonl.stream(inputfile):
        yield Card.Card(**card)  # type: ignore[arg-type]


def cards_from_jsonl_folder(inputfolder) -> Generator[Card, Any, Any]:
    files = glob(str(Path(inputfolder) / "**/*.jsonl"), recursive=True)
    for file in files:
        yield from cards_from_jsonl_file(file)


def cards_from_jsonl(inputfileorfolder) -> Generator[Card, Any, Any]:
    path = Path(inputfileorfolder)
    if path.is_file():
        yield from cards_from_jsonl_file(inputfileorfolder)
    else:
        yield from cards_from_jsonl_folder(inputfileorfolder)
