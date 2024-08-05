"""Test book_to_flashcards module"""

from pathlib import Path
import unittest

from book_to_flashcards import (
    ReverseTextTranslator,
    generate_cards_front_only,
)
from book_to_flashcards.book_to_anki import books_to_anki
from book_to_flashcards.book_to_flashcards import translate_cards


class TestMakingCardsFromFile(unittest.TestCase):
    """Test book_to_flashcards module"""

    testfile = "test/data/dummy_books/dummy_book.txt"
    max_chars = 70

    def test_generate_flashcards_translated(self):
        """Test that we can get a container of card objects from the file"""
        translator = ReverseTextTranslator()
        cards = list(
            generate_cards_front_only(
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
            generate_cards_front_only(
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

        cards = generate_cards_front_only(
            "test/data/dummy_books/dummy_book.txt",
            pipeline="en_core_web_sm",
            maxfieldlen=70,
        )
        cards = translate_cards(cards, translator, "EN-GB")
        books_to_anki(
            cards,
            ankifile="test/output/test.apkg",
            structure=True,
            fontsize=20,
            on_file_complete=None,
        )

    def test_generate_anki_package_notranslate(self):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        Path("test/output/").mkdir(exist_ok=True)
        cards = generate_cards_front_only(
            "test/data/dummy_books/dummy_book.txt",
            pipeline="en_core_web_sm",
            maxfieldlen=70,
        )
        books_to_anki(
            cards,
            ankifile="test/output/test.apkg",
            fontsize=20,
            structure=True,
            on_file_complete=None,
        )


if __name__ == "__main__":
    unittest.main()
