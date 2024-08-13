from pathlib import Path
import unittest

from book_to_flashcards.cli_make_index import tree_item


class TestMakingIndex(unittest.TestCase):
    def test_index(self):
        path = Path(r"test\data\books\dummy_book.txt")
        assert tree_item(path) == "dummy_book.txt"
