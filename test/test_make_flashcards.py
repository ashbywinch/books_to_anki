"""Test book_to_flashcards module"""

from pathlib import Path
import unittest

from book_to_flashcards import (
    ReverseTextTranslator,
    cards_untranslated_from_file,
)
from book_to_flashcards.cards_to_anki import cards_to_anki
from book_to_flashcards.cli_make_flashcards import translate_cards


class TestMakingCardsFromFile(unittest.TestCase):
    """Test book_to_flashcards module"""

    testfile = "test/data/dummy_books/dummy_book.txt"
    max_chars = 70

    def test_generate_flashcards_translated(self):
        """Test that we can get a container of card objects from the file"""
        translator = ReverseTextTranslator()
        cards = list(
            cards_untranslated_from_file(
                self.testfile,
                pipeline="en_core_web_sm",
                maxfieldlen=self.max_chars,
            )
        )
        cards = list(translate_cards(cards, translator, lang="dummy"))
        for card in cards:
            # check that every card has been translated
            self.assertEqual(card.translation, card.current[::-1])
        self.assertEqual(len(cards), 10)

    def test_generate_flashcards_not_translated(self):
        """Test that we can get a container of card objects from the file without translations"""
        cards = list(
            cards_untranslated_from_file(
                self.testfile, pipeline="en_core_web_sm", maxfieldlen=self.max_chars
            )
        )
        for card in cards:
            # check that every card has not been translated
            self.assertEqual(card.translation, "")
        self.assertEqual(len(cards), 10)

    def test_generate_anki_package_translate(self):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        translator = ReverseTextTranslator()
        Path("test/output/").mkdir(exist_ok=True)

        cards = cards_untranslated_from_file(
            "test/data/dummy_books/dummy_book.txt",
            pipeline="en_core_web_sm",
            maxfieldlen=70,
        )
        cards = translate_cards(cards, translator, "EN-GB")
        cards_to_anki(
            cards,
            ankifile="test/output/test.apkg",
            structure=True,
            fontsize=20,
        )

    def test_generate_anki_package_notranslate(self):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        Path("test/output/").mkdir(exist_ok=True)
        cards = cards_untranslated_from_file(
            "test/data/dummy_books/dummy_book.txt",
            pipeline="en_core_web_sm",
            maxfieldlen=70,
        )
        cards_to_anki(
            cards,
            ankifile="test/output/test.apkg",
            fontsize=20,
            structure=True,
        )


if __name__ == "__main__":
    unittest.main()
