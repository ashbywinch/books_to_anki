"""Tests for the finish_translations operational script."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import finish_translations as ft


def test_still_unverified_counts_missing_staging_files(fs, monkeypatch):
    # a recorded book with no staging file is "not re-translated" (stuck or
    # deleted); it must count as still-unverified, not be silently dropped
    listing = Path("/list.txt")
    listing.write_text(
        "# recorded unverified books\nauthor1/book1.jsonl\nauthor2/book2.jsonl\n",
        encoding="utf-8",
    )
    staging = Path("/staging")
    (staging / "author2").mkdir(parents=True)
    (staging / "author2" / "book2.jsonl").write_text("x", encoding="utf-8")
    monkeypatch.setattr(ft, "UNVERIFIED_LIST", listing)
    monkeypatch.setattr(ft, "STAGING", staging)
    # book1 missing from staging -> still unverified (1); book2 exists with a
    # fresh mtime -> re-translated (0)
    assert ft.still_unverified_count() == 1
