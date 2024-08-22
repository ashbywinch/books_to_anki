import subprocess
from sys import platform
import pytest  # type: ignore


class TestClis:
    """Tests for book_complexity module"""

    @pytest.mark.parametrize(
        "source,translate,sink",
        [
            ["text", "dummy", "anki"],
            ["folder", "dummy", "anki"],
            ["jsonfile", "dummy", "anki"],
            ["text", "dummy", "jsonfile"],
            ["folder", "dummy", "jsonfile"],
            ["jsonfile", "dummy", "jsonfile"],
        ],
    )
    def test_book_to_flashcard(self, source: str, translate: str, sink: str, tmp_path):
        params = []
        if source == "text":
            params.extend(["from-text", "test/data/dummy_books/dummy_book.txt"])
        elif source == "folder":
            params.extend(["from-folder", "test/data/dummy_books/"])
        elif source == "jsonfile":
            params.extend(["from-jsonl", "test/data/test.jsonl"])
        else:
            pytest.fail(f"Unknown source {source}")

        if source != "jsonfile":
            params.extend(["pipeline", "--maxfieldlen", "50", "en_core_web_sm"])

        if translate == "dummy":
            params.append("dummy-translate")
        elif translate:
            pytest.fail()

        if sink == "sidebyside":
            params.extend(["to-sidebyside", "--fontsize", "12", tmp_path])
        elif sink == "anki":
            params.extend(["to-anki", "--fontsize", "12", tmp_path / "anki.apkg"])
        elif sink == "jsonfile":
            params.extend(["to-jsonl", tmp_path / "output.jsonl"])
        else:
            pytest.fail(f"Unknown sink: {sink}")

        bin = ".venv/Scripts" if platform == "win32" else ".venv/bin"
        result = subprocess.run(
            [f"{bin}/book-to-flashcard", *params],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
