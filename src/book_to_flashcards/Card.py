from dataclasses import dataclass


@dataclass
class Card:
    """Representing a chunk of text from a book"""

    title: str
    author: str
    start: int
    end: int
    text: str
    translation: str = ""

@dataclass
class Translation:
    card: Card
    translation: str

def trim_title(title:str, separator = None) -> str:
    return title if separator is None else separator.join(title.split(separator)[:-1])

def card_trim_title(card:Card, separator = None) -> Card:
    return Card(
        title = trim_title(card.title, separator),
        author=card.author,
        start = card.start,
        end = card.end,
        text = card.text,
        translation = card.translation
    )
