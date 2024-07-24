"""Test book_to_flashcards module"""

from pathlib import Path
import unittest

from book_to_flashcards import (
    generate_cards,
    ReverseTextTranslator,
    generate_cards_front_only,
    books_to_anki,
)


class TestMakingCardsFromFile(unittest.TestCase):
    """Test book_to_flashcards module"""

    testfile = "test/data/dummy_books/dummy_book.txt"
    max_chars = 70

    def test_generate_flashcards_translated(self):
        """Test that we can get a container of card objects from the file"""
        translator = ReverseTextTranslator()
        with open(self.testfile, "r", encoding="utf-8") as file:
            cards = list(
                generate_cards(
                    file,
                    pipeline="en_core_web_sm",
                    maxfieldlen=self.max_chars,
                    translator=translator,
                    lang="dummy",
                )
            )
            for card in cards:
                # check that every card has been translated
                self.assertEqual(card.translation, card.current[::-1])
            self.assertEqual(len(cards), 10)

    def test_generate_flashcards_not_translated(self):
        """Test that we can get a container of card objects from the file without translations"""
        with open(self.testfile, "r", encoding="utf-8") as file:
            cards = list(
                generate_cards_front_only(
                    file, pipeline="en_core_web_sm", maxfieldlen=self.max_chars
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
        books_to_anki(
            ["test/data/dummy_books/dummy_book.txt"],
            "en_core_web_sm",
            "EN-GB",
            maxfieldlen=70,
            translator=translator,
            structure=True,
            ankifile="test/output/test.apkg",
        )

    def test_generate_anki_package_notranslate(self):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        Path("test/output/").mkdir(exist_ok=True)
        books_to_anki(
            ["test/data/dummy_books/dummy_book.txt"],
            "en_core_web_sm",
            "EN-GB",
            maxfieldlen=70,
            translator=None,
            structure=True,
            ankifile="test/output/test.apkg",
        )


if __name__ == "__main__":
    unittest.main()
