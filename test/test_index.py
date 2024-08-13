from pathlib import Path
import unittest

from book_to_flashcards.cli_make_index import build_tree


class TestMakingIndex(unittest.TestCase):
    def test_index(self):
        tree = build_tree(Path("test") / "data" / "dummy_books")
        self.assertEqual(len(tree), 1)
        for (folder, children) in tree.items():
            self.assertEqual(folder, "dummy_books")
            self.assertEqual(len(children), 2)
            self.assertEqual(children[0], "dummy_book.txt")
            self.assertEqual(children[1], "second_dummy_book.txt")
            break