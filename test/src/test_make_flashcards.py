"""Test book_to_flashcards module"""

import pytest  # type: ignore


from book_to_flashcards import (
    ReverseTextTranslator,
    cards_untranslated_from_file,
)
from book_to_flashcards.cards_to_anki import cards_to_anki
from book_to_flashcards.cli_make_flashcards import translate_cards
from book_to_flashcards.cards_jsonl import cards_from_jsonl, cards_to_jsonl  # type: ignore


class TestMakingCardsFromFile:
    """Test book_to_flashcards module"""

    testTextFile = "test/data/dummy_books/dummy_book.txt"
    max_chars = 70

    def test_generate_flashcards_translated(self):
        """Test that we can get a container of card objects from the file"""
        translator = ReverseTextTranslator()
        cards = list(
            cards_untranslated_from_file(
                self.testTextFile,
                pipeline="en_core_web_sm",
                maxfieldlen=self.max_chars,
            )
        )
        cards = list(translate_cards(cards, translator, lang="dummy"))
        for card in cards:
            # check that every card has been translated
            assert card.translation == card.text[::-1]
        assert len(cards) == 10

    def test_generate_flashcards_not_translated(self):
        """Test that we can get a container of card objects from the file without translations"""
        cards = list(
            cards_untranslated_from_file(
                self.testTextFile, pipeline="en_core_web_sm", maxfieldlen=self.max_chars
            )
        )
        for card in cards:
            # check that every card has not been translated
            assert card.translation == ""
        for card in cards[1:]:
            assert card.index_in_file > 0
        assert len(cards) == 10

    def test_generate_anki_package_translate(self, tmp_path):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        translator = ReverseTextTranslator()

        cards = cards_untranslated_from_file(
            self.testTextFile,
            pipeline="en_core_web_sm",
            maxfieldlen=70,
        )
        cards = translate_cards(cards, translator, "EN-GB")
        cards_to_anki(
            cards,
            ankifile=tmp_path / "test.apkg",
            structure=True,
            fontsize=20,
        )

    def test_generate_anki_package_notranslate(self, tmp_path):
        """Don't know how to validate an anki package, but at least we can check
        that the code doesn't fall over"""
        cards = cards_untranslated_from_file(
            "test/data/dummy_books/dummy_book.txt",
            pipeline="en_core_web_sm",
            maxfieldlen=70,
        )
        cards_to_anki(
            cards,
            ankifile=tmp_path / "test.apkg",
            fontsize=20,
            structure=True,
        )

    @pytest.mark.parametrize(
        "translate,sink", [("dummy", "jsonl"), ("dummy", "jsonls")]
    )
    def test_book_to_flashcard_roundtrip(self, translate: str, sink: str, tmp_path):
        cardsin = cards_from_jsonl("test/data/dummy_books/")
        if translate == "dummy":
            cardsin = translate_cards(cardsin, ReverseTextTranslator(), "dummy")
        elif translate is not None:
            pytest.fail(f"Unsupported translator {translate}")

        if sink == "jsonl":
            cards_to_jsonl(cardsin, tmp_path / "output.jsonl")
            cardsout = cards_from_jsonl(tmp_path / "output.jsonl")
        elif sink == "jsonls":
            cards_to_jsonl(cardsin, tmp_path / "jsonl/")
            cardsout = cards_from_jsonl(tmp_path / "jsonl")
        else:
            pytest.fail(f"Can't round trip sink: {sink}")
        assert len(list(cardsin)) == len(list(cardsout))
        for a, b in zip(cardsin, cardsout):
            assert a == b
