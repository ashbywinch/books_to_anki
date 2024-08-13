from pathlib import Path
import shutil
import unittest
import subprocess
from sys import platform
from parameterized import parameterized


class TestClis(unittest.TestCase):
    """Tests for book_complexity module"""

    testOutput = Path("test/output/")

    def setUp(self):
        
        if self.testOutput.exists():
            shutil.rmtree(self.testOutput)
            
        self.testOutput.mkdir(exist_ok=True)


    @parameterized.expand(
        [
            ["text", "dummy", "anki"],
            ["folder", "dummy", "anki"],
            ["jsonfile", "dummy", "anki"],
            ["text", "dummy", "jsonfile"],
            ["folder", "dummy", "jsonfile"],
            ["jsonfile", "dummy", "jsonfile"],
        ]
    )


    def test_book_to_flashcard(
        self, source: str = "text", translate: str = "dummy", sink: str = "jsonl", roundtrip: bool = True
    ):
        params = []
        if source == "text":
            params.extend(["from-text", "test/data/dummy_books/dummy_book.txt"])
        elif source == "folder":
            params.extend(["from-folder", "test/data/dummy_books/"])
        elif source == "jsonfile":
            params.extend(["from-jsonl", "test/data/test.jsonl"])
        else:
            self.fail(f"Unknown source {source}")

        if source != "jsonfile":
            params.extend(["pipeline", "--maxfieldlen", "50", "en_core_web_sm"])

        if translate == "dummy":
            params.append("dummy-translate")
        elif translate:
            self.fail()

        Path("test/output").mkdir(parents=True, exist_ok=True)
        if sink == "sidebyside":
            params.extend(["to-sidebyside", "--fontsize", "12", "test/output"])
        elif sink == "anki":
            params.extend(["to-anki", "--fontsize", "12", "test/output/anki.apkg"])
        elif sink == "jsonfile":
            params.extend(["to-jsonl", "test/output/output.jsonl"])
        else:
            self.fail(f"Unknown sink: {sink}")

        print(" ".join(params))

        bin = ".env/Scripts" if platform == "win32" else ".env/bin"
        result = subprocess.run(
            [f"{bin}/book-to-flashcard", *params],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        