"""Tests for the Anki deck writer's failure handling."""




from book_to_flashcards.Card import Card
from book_to_flashcards.cards_to_anki import cards_to_anki


def test_value_error_mid_deck_still_writes_apkg(tmp_path):
    # the translator surfaces malformed-response and misalignment failures as
    # ValueError/TypeError after retry/split exhaustion; a mid-deck failure
    # must still preserve the cards translated so far, same as
    # OpenCodeGoError
    out = tmp_path / "deck.apkg"

    def cards():
        c = Card(title="t", author="a", start=0, end=3, text="abc")
        c.translation = "translated"
        yield c
        raise ValueError("batch rejected after split recovery")

    cards_to_anki(cards(), structure=False, ankifile=str(out), fontsize=12)
    assert out.exists()
    assert out.stat().st_size > 0
    # the deck contains the collection written despite the mid-stream failure
    import zipfile

    assert "collection.anki2" in zipfile.ZipFile(out).namelist()
