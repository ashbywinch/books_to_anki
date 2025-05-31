"""Tests for Card.py module in book_to_flashcards."""

import pytest
from book_to_flashcards.Card import Card, card_trim_title


class TestCardDataclass:
    def test_card_creation_all_fields(self):
        card = Card(
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
            start=100,
            end=200,
            text="A sentence from the book.",
            translation="Une phrase du livre."
        )
        assert card.title == "The Great Gatsby"
        assert card.author == "F. Scott Fitzgerald"
        assert card.start == 100
        assert card.end == 200
        assert card.text == "A sentence from the book."
        assert card.translation == "Une phrase du livre."

    def test_card_creation_minimal_fields(self):
        # translation is optional and defaults to ""
        card = Card(
            title="1984",
            author="George Orwell",
            start=0,
            end=50,
            text="War is peace."
        )
        assert card.title == "1984"
        assert card.author == "George Orwell"
        assert card.start == 0
        assert card.end == 50
        assert card.text == "War is peace."
        assert card.translation == "" # Default value

    def test_card_equality(self):
        card1 = Card("T", "A", 1, 2, "Text")
        card2 = Card("T", "A", 1, 2, "Text")
        card3 = Card("T2", "A", 1, 2, "Text")
        card4 = Card("T", "A2", 1, 2, "Text")
        card5 = Card("T", "A", 10, 2, "Text")
        card6 = Card("T", "A", 1, 20, "Text")
        card7 = Card("T", "A", 1, 2, "Text2")
        card8 = Card("T", "A", 1, 2, "Text", "Trans")

        assert card1 == card2
        assert card1 != card3
        assert card1 != card4
        assert card1 != card5
        assert card1 != card6
        assert card1 != card7
        assert card1 != card8
        card2.translation = "Trans"
        assert card1 != card2 # Now card2 has translation
        assert card2 == card8


class TestCardTrimTitleFunction:
    @pytest.fixture
    def sample_card(self):
        return Card(
            title="BookTitle_Part1_Part2",
            author="Test Author",
            start=0, end=10,
            text="Sample text"
        )

    def test_card_trim_title_with_separator(self, sample_card):
        trimmed_card = card_trim_title(sample_card, separator="_")
        assert trimmed_card.title == "BookTitle_Part1"
        # Ensure other fields are preserved
        assert trimmed_card.author == sample_card.author
        assert trimmed_card.text == sample_card.text
        assert trimmed_card.start == sample_card.start
        assert trimmed_card.end == sample_card.end
        assert trimmed_card.translation == sample_card.translation

    def test_card_trim_title_no_separator_provided(self, sample_card):
        # trim_title (the helper) returns original if separator is None
        trimmed_card = card_trim_title(sample_card, separator=None)
        assert trimmed_card.title == "BookTitle_Part1_Part2"
        assert trimmed_card.author == sample_card.author # Check another field

    def test_card_trim_title_separator_not_in_title(self, sample_card):
        original_title = "SimpleTitleNoSeparator"
        card_no_sep = Card(original_title, "A", 0,0, "t")
        trimmed_card = card_trim_title(card_no_sep, separator="-")
        assert trimmed_card.title == original_title

    def test_card_trim_title_returns_new_card_instance(self, sample_card):
        trimmed_card = card_trim_title(sample_card, separator="_")
        assert trimmed_card is not sample_card

# We already have extensive tests for trim_title itself in test_book_complexity.py
# so we don't need to repeat all edge cases for it here, just ensure card_trim_title uses it. 