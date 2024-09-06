from dataclasses import dataclass


@dataclass
class Card:
    """Representing a single flash card (or 'Note' in Anki)"""

    filename: str
    index_in_file: int
    text: str
    translation: str = ""

@dataclass
class Translation:
    card: Card
    translation: str