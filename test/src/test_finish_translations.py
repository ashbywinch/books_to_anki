"""Tests for the finish_translations operational script."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import finish_translations as ft


def test_still_unverified_counts_missing_staging_files(fs):
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
    # book1 missing from staging -> still unverified (1); book2 exists with a
    # fresh mtime -> re-translated (0)
    assert ft.still_unverified_count(staging=staging, unverified_list=listing) == 1


def test_run_mop_up_clean_run(tmp_path):
    # subprocess-based (the driver runs a child process that sees the real
    # filesystem) — tmp_path, not pyfakefs
    batch_log = tmp_path / "batch.log"
    batch_log.write_text("", encoding="utf-8")
    assert ft.run_mop_up(driver=["/bin/true"], batch_log=batch_log) == set()


def test_run_mop_up_driver_failure_without_failures(tmp_path):
    # driver exits non-zero without logging any per-book failures (e.g. the
    # translator constructor raises on a missing API key): the mop-up must
    # surface a driver-level failure, not report a clean run
    batch_log = tmp_path / "batch.log"
    batch_log.write_text("", encoding="utf-8")
    assert ft.run_mop_up(driver=["/bin/false"], batch_log=batch_log) is None
