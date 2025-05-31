from collections.abc import Generator
from glob import glob
import os
from typing import Any
from pathlib import Path
import orjsonl as jsonl
import orjson
import dataclasses

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


def cards_to_jsonl(cards, outputfileorfolder_str: str, separator: str="", progress=None):
    path = Path(outputfileorfolder_str)

    if path.is_dir(): # Case 1: Existing directory
        cards_to_jsonl_folder(cards, str(path), separator, progress)
    elif path.suffix: # Case 2: Has a suffix (e.g. .jsonl), treat as file.
                      # jsonl.save inside cards_to_jsonl_file will handle FileNotFoundError if parent doesn't exist.
        cards_to_jsonl_file(cards, str(path), progress)
    else: # Case 3: Not an existing directory AND no suffix. Treat as new directory to be created.
        path.mkdir(parents=True, exist_ok=True) # Create the directory
        cards_to_jsonl_folder(cards, str(path), separator, progress)


def cards_from_jsonl_file(inputfile) -> Generator[Card.Card, Any, Any]:
    card_fields = {f.name for f in dataclasses.fields(Card.Card)}
    for item_dict in jsonl.stream(inputfile):         
        # Filter to only include known Card fields to prevent unexpected keyword arguments
        filtered_item = {k: v for k, v in item_dict.items() if k in card_fields}
        
        try:
            yield Card.Card(**filtered_item)
        except TypeError:
            # This will catch cases where filtered_item is missing required fields for Card
            # or if there are other type-related issues during instantiation.
            # print(f"Skipping card due to TypeError: {filtered_item}") # Optional: for debugging
            continue


def cards_from_jsonl_folder(inputfolder) -> Generator[Card.Card, Any, Any]:
    files = glob(str(Path(inputfolder) / "**/*.jsonl"), recursive=True)
    for file_path in files:
        try:
            yield from cards_from_jsonl_file(file_path)
        except FileNotFoundError: 
            continue
        except orjson.JSONDecodeError: # If jsonl.stream in cards_from_jsonl_file fails for a file
            # print(f"Skipping file due to JSON decode error: {file_path}") # Optional
            continue # Skip this entire file and proceed to the next


def cards_from_jsonl(inputfileorfolder) -> Generator[Card.Card, Any, Any]:
    path = Path(inputfileorfolder)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {inputfileorfolder}")

    if path.is_file():
        yield from cards_from_jsonl_file(inputfileorfolder)
    else: # path.is_dir()
        yield from cards_from_jsonl_folder(inputfileorfolder)
