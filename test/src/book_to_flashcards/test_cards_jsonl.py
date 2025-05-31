"""Tests for cards_jsonl.py in book_to_flashcards."""

import pytest
import orjsonl
import orjson
from pathlib import Path

from book_to_flashcards.Card import Card
from book_to_flashcards.cards_jsonl import cards_to_jsonl, cards_from_jsonl

@pytest.fixture
def sample_cards():
    return [
        Card("Book A", "Author X", 0, 1, "Text A1", "Trans A1"),
        Card("Book A", "Author X", 1, 2, "Text A2", "Trans A2"),
        Card("Book B", "Author Y", 0, 1, "Text B1", "Trans B1"),
    ]

@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    # tmp_path is a pytest fixture providing a temporary directory unique to the test invocation
    output_dir = tmp_path / "jsonl_output"
    output_dir.mkdir()
    return output_dir


class TestCardsToJsonl:
    def test_cards_to_jsonl_single_file_output(self, sample_cards, temp_output_dir):
        output_file = temp_output_dir / "all_cards.jsonl"
        cards_to_jsonl(sample_cards, output_file)

        assert output_file.exists()
        # Read back and verify - orjsonl.load returns a list of dicts
        loaded_cards_data = orjsonl.load(output_file)
        assert len(loaded_cards_data) == len(sample_cards)
        for i, card_data in enumerate(loaded_cards_data):
            original_card = sample_cards[i]
            assert card_data["title"] == original_card.title
            assert card_data["text"] == original_card.text
            assert card_data["translation"] == original_card.translation
    
    def test_cards_to_jsonl_directory_output_per_title(self, sample_cards, temp_output_dir):
        cards_to_jsonl(sample_cards, temp_output_dir) # Pass directory path

        # Files are expected to be in author subdirectories
        book_a_file = temp_output_dir / sample_cards[0].author / "Book A.jsonl"
        book_b_file = temp_output_dir / sample_cards[2].author / "Book B.jsonl"

        assert book_a_file.exists(), f"File not found: {book_a_file}"
        assert book_b_file.exists(), f"File not found: {book_b_file}"

        book_a_data = orjsonl.load(book_a_file)
        assert len(book_a_data) == 2
        assert book_a_data[0]["text"] == "Text A1"
        assert book_a_data[1]["text"] == "Text A2"

        book_b_data = orjsonl.load(book_b_file)
        assert len(book_b_data) == 1
        assert book_b_data[0]["text"] == "Text B1"

    def test_cards_to_jsonl_empty_list_of_cards_single_file(self, temp_output_dir):
        output_file = temp_output_dir / "empty.jsonl"
        cards_to_jsonl([], output_file)
        assert output_file.exists()
        assert output_file.read_text() == "" 

    def test_cards_to_jsonl_empty_list_of_cards_directory_output(self, temp_output_dir):
        cards_to_jsonl([], temp_output_dir)
        # No files should be created in the directory if the card list is empty
        # as it groups by title, and there are no titles.
        assert not list(temp_output_dir.iterdir()) # Check if directory is empty

    def test_cards_to_jsonl_target_dir_does_not_exist_for_file(self, sample_cards, tmp_path):
        # Test writing a single file to a non-existent subdir
        non_existent_subdir = tmp_path / "non_existent_subdir"
        output_file = non_existent_subdir / "cards.jsonl"
        
        # The new dispatch logic in cards_to_jsonl means that if the parent dir for a file doesn't exist,
        # orjsonl.save will raise an error. For xopen, it's often FileNotFoundError or IsADirectoryError,
        # depending on the exact path structure and if parts of it exist as files.
        # For orjsonl, it's likely to be a FileNotFoundError or similar OSError if the parent cannot be written to.
        with pytest.raises(Exception): # Broad exception, as orjsonl might raise various OS related errors
             cards_to_jsonl(sample_cards, output_file)


class TestCardsFromJsonl:
    def test_cards_from_jsonl_single_file(self, sample_cards, temp_output_dir):
        output_file = temp_output_dir / "data.jsonl"
        # Use cards_to_jsonl to create a valid file first
        cards_to_jsonl(sample_cards, output_file)

        loaded_cards = list(cards_from_jsonl(output_file))
        assert len(loaded_cards) == len(sample_cards)
        for i, card in enumerate(loaded_cards):
            assert isinstance(card, Card)
            assert card.title == sample_cards[i].title
            assert card.text == sample_cards[i].text

    def test_cards_from_jsonl_directory(self, sample_cards, temp_output_dir):
        # Use cards_to_jsonl to create files in directory mode
        cards_to_jsonl(sample_cards, temp_output_dir)

        loaded_cards = list(cards_from_jsonl(temp_output_dir))
        assert len(loaded_cards) == len(sample_cards)
        
        # Check if all original card texts are present in the loaded cards
        original_texts = {c.text for c in sample_cards}
        loaded_texts = {c.text for c in loaded_cards}
        assert original_texts == loaded_texts

    def test_cards_from_jsonl_empty_file(self, temp_output_dir):
        empty_file = temp_output_dir / "empty.jsonl"
        empty_file.write_text("")
        loaded_cards = list(cards_from_jsonl(empty_file))
        assert len(loaded_cards) == 0

    def test_cards_from_jsonl_malformed_json_line(self, temp_output_dir):
        malformed_file = temp_output_dir / "malformed.jsonl"
        # Valid JSON, then invalid, then valid Card-like dict
        # Card needs: title, author, start, end, text. Translation is optional.
        valid_card_dict1 = {"title": "T1", "author": "A1", "start": 0, "end": 1, "text": "Valid1"}
        valid_card_dict2 = {"title": "T2", "author": "A2", "start": 0, "end": 1, "text": "Valid2", "translation": ""}
        
        file_content = (
            orjson.dumps(valid_card_dict1).decode() + "\n"
            "this is not json\n" +
            orjson.dumps(valid_card_dict2).decode()
        )
        malformed_file.write_text(file_content)

        # jsonl.stream will fail on the first bad line ("this is not json").
        # The error orjson.JSONDecodeError will be raised from within jsonl.stream.
        with pytest.raises(orjson.JSONDecodeError):
            list(cards_from_jsonl(malformed_file))

    def test_cards_from_jsonl_missing_fields_in_json(self, temp_output_dir):
        partial_file = temp_output_dir / "partial.jsonl"
        # Missing 'author' and 'start' which are required by Card constructor
        partial_card_dict = {"title": "PartialBook", "end": 10, "text": "Partial Text"}
        partial_file.write_text(orjson.dumps(partial_card_dict).decode())

        loaded_cards = list(cards_from_jsonl(partial_file))
        assert len(loaded_cards) == 0 # Expect TypeError to be caught, so no card yielded
        
        # Test with one good, one bad
        good_card_dict = {"title": "T1", "author": "A1", "start": 0, "end": 1, "text": "Good"}
        partial_file.write_text(orjson.dumps(good_card_dict).decode() + "\n" + orjson.dumps(partial_card_dict).decode())
        loaded_cards = list(cards_from_jsonl(partial_file))
        assert len(loaded_cards) == 1
        assert loaded_cards[0].text == "Good"

    def test_cards_from_jsonl_extra_fields_in_json(self, temp_output_dir):
        extra_file = temp_output_dir / "extra.jsonl"
        extra_card_dict = {"title": "T", "author": "A", "start": 0, "end": 1, "text": "Extra", "extra_field": "ignore_me"}
        extra_file.write_text(orjson.dumps(extra_card_dict).decode())

        loaded_cards = list(cards_from_jsonl(extra_file))
        assert len(loaded_cards) == 1
        assert loaded_cards[0].text == "Extra"
        assert not hasattr(loaded_cards[0], "extra_field")

    def test_cards_from_jsonl_directory_no_jsonl_files(self, temp_output_dir):
        (temp_output_dir / "not_a_jsonl.txt").write_text("hello")
        loaded_cards = list(cards_from_jsonl(temp_output_dir))
        assert len(loaded_cards) == 0

    def test_cards_from_jsonl_non_existent_path(self):
        with pytest.raises(FileNotFoundError): 
            list(cards_from_jsonl(Path("non_existent_path_12345.jsonl")))
        with pytest.raises(FileNotFoundError):
            list(cards_from_jsonl(Path("non_existent_dir_12345/")))