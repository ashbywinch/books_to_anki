#!/usr/bin/env python3
"""Keep the translation batch running until the translations are finished.

Wakes every 15 minutes. While the batch process is alive it does nothing;
if the process disappears it checks whether the driver logged its final
"finished:" summary after this keep-alive started. If the batch died without
finishing, it is relaunched (the driver resumes from its checkpoint, so a
restart only redoes the in-flight book). Exits once a finished summary
appears.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
BATCH_LOG = HERE / "translate-batch.log"
KEEPALIVE_LOG = HERE / "translate-keepalive.log"
BATCH_CMD = [
    sys.executable,
    "-m",
    "book_to_flashcards.translate_books",
    "--input",
    "/home/ashby/Documents/code/side-by-side/public/api/books/ru",
    "--output",
    str(HERE / "data/translations-site"),
    "--workers",
    "4",
]
INTERVAL_SECONDS = 15 * 60
PROC_PATTERN = "book_to_flashcards.translate_books"


def log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
    with open(KEEPALIVE_LOG, "a", encoding="utf-8") as fh:
        fh.write(line)


def batch_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", PROC_PATTERN], capture_output=True, text=True, check=False
    )
    return bool(result.stdout.strip())


def staging_books() -> int:
    return len(list((HERE / "data/translations-site").glob("*/*.jsonl")))


def main() -> int:
    start_size = BATCH_LOG.stat().st_size if BATCH_LOG.exists() else 0
    log(f"keep-alive started (interval {INTERVAL_SECONDS}s, watching {BATCH_LOG})")
    while True:
        time.sleep(INTERVAL_SECONDS)
        if batch_running():
            log(f"batch running; {staging_books()} books in staging")
            continue
        # process gone: finished normally, or died?
        if BATCH_LOG.exists():
            with open(BATCH_LOG, encoding="utf-8") as fh:
                fh.seek(start_size)
                tail = fh.read()
            if "finished:" in tail:
                log(
                    f"translations finished; {staging_books()} books in staging. "
                    "keep-alive exiting"
                )
                return 0
        log("batch process gone without a finished summary — relaunching")
        with open(BATCH_LOG, "a", encoding="utf-8") as log_fh:
            proc = subprocess.Popen(
                BATCH_CMD,
                cwd=HERE,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        log(f"relaunched batch (pid {proc.pid})")


if __name__ == "__main__":
    raise SystemExit(main())
