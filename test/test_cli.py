import unittest
import subprocess
from parameterized import parameterized


class TestClis(unittest.TestCase):
    """Tests for book_complexity module"""

    @parameterized.expand(
        [
            [
                "text",
                "dummy",
                "csv",
            ],
            ["folder", "dummy", "csv"],
            ["csv", "dummy", "csv"],
            ["text", "dummy", "anki"],
            ["folder", "dummy", "anki"],
            ["csv", "dummy", "anki"],
            ["text", "dummy", "sidebyside"],
            ["folder", "dummy", "sidebyside"],
            ["csv", "dummy", "sidebyside"],
        ]
    )
    def test_book_to_flashcard(
        self, source: str = "text", translate: str = "dummy", sink: str = "csv"
    ):
        params = []
        if source == "text":
            params.extend(["from-text", "test/data/dummy_books/dummy_book.txt"])
        elif source == "folder":
            params.extend(["from-folder", "test/data/dummy_books/"])
        elif source == "csv":
            params.extend(["from-csv", "test/data/test.csv"])
        else:
            self.fail()

        if source != "csv":
            params.extend(["pipeline", "--maxfieldlen", "50", "en_core_web_sm"])

        if translate == "dummy":
            params.append("dummy-translate")
        elif translate:
            self.fail()

        if sink == "csv":
            params.extend(["to-csv", "output.csv"])
        elif sink == "sidebyside":
            params.extend(["to-sidebyside", "--fontsize", "12", "."])
        elif sink == "anki":
            params.extend(["to-anki", "--fontsize", "12", "anki.apkg"])
        else:
            self.fail()

        print(" ".join(params))
        result = subprocess.run(["book-to-flashcard", *params])
        self.assertEqual(result.returncode, 0)
