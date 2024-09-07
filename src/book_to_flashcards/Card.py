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