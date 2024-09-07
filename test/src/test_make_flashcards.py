"""Test book_to_flashcards module"""

import glob
import os
from pathlib import Path
import pytest  # type: ignore


from book_to_flashcards import (
    ReverseTextTranslator,
    cards_untranslated_from_file,
)
from book_to_flashcards.cards_to_anki import cards_to_anki
from book_to_flashcards.cli_make_flashcards import translate_cards
from book_to_flashcards.cards_jsonl import cards_from_jsonl, cards_to_jsonl  # type: ignore


@pytest.fixture
def inputfolder():
    yield Path("test/data/dummy_books/")


@pytest.fixture
def outputfolder(fs):
    p = Path("output/")
    os.mkdir(p)
    yield p


@pytest.fixture
def test_cards(fs, inputfolder):
    fs.pause()  # need to read the real fs to find files to put in fake fs
    inputfiles = [f for f in glob.glob(str(inputfolder / "**/*.txt"), recursive=True)]
    for f in inputfiles:
        fs.add_real_file(f)

    # and we'll read the cards from the real FS or it confuses Spacy
    cards = []
    for f in inputfiles:
        cards.extend(
            cards_untranslated_from_file(f, pipeline="en_core_web_sm", maxfieldlen=30)
        )
    fs.resume()
    assert len(cards) == 23
    yield cards


@pytest.fixture
def test_cards_translated(test_cards):
    yield list(translate_cards(test_cards, ReverseTextTranslator(), "dummy"))


class TestMakingCardsFromFile:
    """Test book_to_flashcards module"""

    def test_generate_flashcards_translated(self, test_cards_translated):
        """Test that we can get a container of card objects from the file"""

        for card in test_cards_translated:
            # check that every card has been translated
            assert card.translation == card.text[::-1]
        assert len(test_cards_translated) == 23

    def test_generate_flashcards_not_translated(self, test_cards):
        """Test that we can get a container of card objects from the file without translations"""
        for card in test_cards:
            # check that every card has not been translated
            assert card.translation == ""

    def test_index_in_file(self, test_cards, inputfolder):
        dummy_book = inputfolder / "dummy_book.txt"
        cards_single_book = [
            card for card in test_cards if card.title == "dummy_book"
        ]
        for card in cards_single_book[1:]:
            assert card.start > 0
        assert len(cards_single_book) == 21

    def test_generate_anki_package_translate(self, test_cards_translated, outputfolder):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        cards_to_anki(
            test_cards_translated,
            ankifile=outputfolder / "test.apkg",
            structure=True,
            fontsize=20,
        )

    def test_generate_anki_package_notranslate(self, test_cards, outputfolder):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        cards_to_anki(
            test_cards,
            ankifile=outputfolder / "test.apkg",
            fontsize=20,
            structure=True,
        )

    def test_book_to_flashcard_roundtrip_jsonl(
        self, test_cards_translated, outputfolder
    ):
        cards_to_jsonl(test_cards_translated, outputfolder / "output.jsonl")
        cardsout = list(cards_from_jsonl(outputfolder / "output.jsonl"))
        assert test_cards_translated == cardsout

    def test_book_to_flashcard_roundtrip_jsonls(
        self, test_cards_translated, outputfolder
    ):
        cards_to_jsonl(test_cards_translated, outputfolder / "jsonl/")
        cardsout = list(cards_from_jsonl(outputfolder / "jsonl"))
        assert test_cards_translated == cardsout

    def test_book_to_flashcard_roundtrip_overwrite_jsonls(
        self, test_cards_translated, inputfolder
    ):
        inputfiles = len(
            [f for f in glob.glob(str(inputfolder / "**/*.txt"), recursive=True)]
        )
        cards_to_jsonl(
            test_cards_translated, inputfolder
        )  # in fakefs so won't overwrite real data
        cardsout = list(cards_from_jsonl(inputfolder))
        assert test_cards_translated == cardsout
        outputfiles = len(
            [f for f in glob.glob(str(inputfolder / "**/*.txt"), recursive=True)]
        )
        assert inputfiles == outputfiles == 2
