"""Defines core data structures for representing flashcards and related utility functions.

This module contains dataclasses for `Card` (representing a piece of text extracted
for a flashcard). It also includes utility functions for manipulating card titles.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Card:
    """Represents a single flashcard, typically a segment of text from a book.

    Attributes:
        title: The title of the source book or document.
        author: The author of the source book or document.
        start: The starting character offset of the text segment in the original source.
        end: The ending character offset of the text segment in the original source.
        text: The actual text content of the flashcard (the "front" of the card).
        translation: The translated version of `text` (the "back" of the card).
                     Defaults to an empty string if no translation is available.
    """

    title: str
    author: str
    start: int  # Character offset within original text
    end: int    # Character offset within original text
    text: str
    translation: str = ""


def trim_title(title: str, separator: Optional[str] = None) -> str:
    """Trims a title string by removing the last segment after a specified separator.

    If no separator is provided, or if the separator is not in the title,
    the original title is returned.

    Args:
        title: The title string to trim.
        separator: The string at which to split and trim the title. If None,
                   no trimming occurs.

    Returns:
        The trimmed title string. For example, `trim_title("Part1_Part2_End", "_")`
        would return "Part1_Part2".
    """
    if separator is None or separator not in title:
        return title
    return separator.join(title.split(separator)[:-1])


def card_trim_title(card: Card, separator: Optional[str] = None) -> Card:
    """Creates a new Card object with its title trimmed.

    Applies the `trim_title` function to the `card.title` attribute.
    All other attributes of the card are preserved in the new Card instance.

    Args:
        card: The input `Card` object.
        separator: The string separator to use for trimming the title, passed to `trim_title`.
                   If None, the title is not trimmed.

    Returns:
        A new `Card` object with the potentially trimmed title.
    """
    return Card(
        title=trim_title(card.title, separator),
        author=card.author,
        start=card.start,
        end=card.end,
        text=card.text,
        translation=card.translation
    )