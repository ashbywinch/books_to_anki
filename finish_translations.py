#!/usr/bin/env python3
"""Finish the translation batch, mop up failed books, copy results to the site.

1. Wait for the running batch to finish (its "finished:" summary appears and
   the process exits).
2. Mop up: re-run the driver until no book fails, or the same books fail twice
   in a row (those are reported as stuck rather than retried forever).
3. Copy the staging output into the site's public/api/books/ru.
4. Re-flag the "translated" field in index.jsonl.
5. Write a summary to finish-translations.log, including how many of the
   originally-unverified books were NOT re-translated by the verified runs
   (the reprocessing decision set).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
BATCH_LOG = HERE / "translate-batch.log"
STAGING = HERE / "data/translations-site"
SITE = Path("/home/ashby/Documents/code/side-by-side/public/api/books/ru")
UNVERIFIED_LIST = HERE / "unverified-books.txt"
SUMMARY_LOG = HERE / "finish-translations.log"
DRIVER = [
    sys.executable,
    "-m",
    "book_to_flashcards.translate_books",
    "--input",
    str(SITE),
    "--output",
    str(STAGING),
    "--workers",
    "4",
    # smaller batches: the dense prose giants fail ~40% of 60-card calls;
    # batch 30 roughly halves the retry storms (measured ~2.4x throughput)
    "--batch-size",
    "30",
]
POLL_SECONDS = 5 * 60
# the unverified run's window (machine-local time)
LOCAL_TZ = datetime.now().astimezone().tzinfo
UNVERIFIED_END = datetime(2026, 8, 1, 6, 9, 0, tzinfo=LOCAL_TZ)


def log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
    with open(SUMMARY_LOG, "a", encoding="utf-8") as fh:
        fh.write(line)
    print(line, end="")


def batch_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", "book_to_flashcards.translate_books"],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def keepalive_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", "translate_keepalive"],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def wait_for_batch_to_finish() -> None:
    """Wait until it is safe to start the mop-up driver.

    The mop-up driver is the same program as the batch, so two must never run
    at once. Wait while a batch runs; if the batch dies without a finished
    summary, the keep-alive script relaunches it, so also wait while the
    keep-alive is alive (it exits once it sees a finished summary). Only
    proceed when neither is running.
    """
    while batch_running() or keepalive_running():
        time.sleep(POLL_SECONDS)
    log("no batch or keep-alive running; proceeding to mop-up")


def parse_failures(segment_start: int) -> set[str]:
    """Book identifiers that failed or crashed in the log segment."""
    import re

    failures: set[str] = set()
    with open(BATCH_LOG, encoding="utf-8") as fh:
        fh.seek(segment_start)
        for line in fh:
            m = re.search(r"ERROR (?:book )?(/.*?\.jsonl)", line)
            if m:
                failures.add(m.group(1))
    return failures


def run_mop_up() -> set[str]:
    """Re-run the driver until no failures, or the same set fails twice."""
    failures: set[str] = set()
    for attempt in range(1, 7):
        segment_start = BATCH_LOG.stat().st_size if BATCH_LOG.exists() else 0
        log(f"mop-up attempt {attempt}: running driver")
        with open(BATCH_LOG, "a", encoding="utf-8") as fh:
            proc = subprocess.run(DRIVER, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT, check=False)
        new_failures = parse_failures(segment_start)
        log(
            f"mop-up attempt {attempt}: exit={proc.returncode}, "
            f"{len(new_failures)} failed books"
        )
        if not new_failures:
            return set()
        if new_failures == failures:
            log(f"failed set unchanged ({len(new_failures)} books); stopping mop-up")
            return new_failures
        failures = new_failures
    log(f"mop-up attempts exhausted; {len(failures)} books still failing")
    return failures


def copy_staging_to_site() -> int:
    copied = 0
    for f in sorted(STAGING.glob("*/*.jsonl")):
        dest = SITE / f.parent.name / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        copied += 1
    return copied


def flag_translated() -> int:
    def translated_status(author: str, title: str) -> bool:
        p = SITE / author / f"{title}.jsonl"
        if not p.exists():
            return False
        return all(
            json.loads(l).get("translation")
            for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()
        )

    idx_path = SITE / "index.jsonl"
    entries = [
        json.loads(l)
        for l in idx_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    n_translated = 0
    for b in entries:
        b["translated"] = translated_status(b["author"], b["title"])
        n_translated += 1 if b["translated"] else 0
    idx_path.write_text(
        "\n".join(json.dumps(b, ensure_ascii=False, separators=(",", ":")) for b in entries)
        + "\n",
        encoding="utf-8",
    )
    return n_translated


def still_unverified_count() -> int:
    """Of the recorded unverified books, how many were NOT re-translated since?"""
    if not UNVERIFIED_LIST.exists():
        return 0
    rels = [
        l.strip()
        for l in UNVERIFIED_LIST.read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]
    still = 0
    for rel in rels:
        p = STAGING / rel
        if p.exists():
            mt = datetime.fromtimestamp(p.stat().st_mtime, tz=LOCAL_TZ)
            if mt < UNVERIFIED_END:
                still += 1
    return still


def main() -> int:
    log("orchestrator started: waiting for the current pass to finish")
    wait_for_batch_to_finish()

    log("mop-up phase starting")
    stuck = run_mop_up()

    log("copying staging to site")
    copied = copy_staging_to_site()
    n_translated = flag_translated()
    still_unverified = still_unverified_count()

    log(
        f"done: {copied} books copied to site, {n_translated} books flagged "
        f"translated, {len(stuck)} books stuck, {still_unverified} of the "
        f"recorded unverified books not yet re-translated"
    )
    if stuck:
        log("stuck books:")
        for s in sorted(stuck):
            log(f"  {s}")
    return 1 if stuck else 0


if __name__ == "__main__":
    raise SystemExit(main())
