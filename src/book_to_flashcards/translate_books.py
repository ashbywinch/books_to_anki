"""Translate whole books of untranslated cards from a jsonl folder, in parallel.

Walks a folder of per-book jsonl files (one Card per line), translates every
card that is missing a translation, and writes each completed book to an
output folder mirroring the input layout. Books are processed in parallel by a
thread pool; a single book is always translated sequentially so batch context
stays within that book.

Resume-safe: a book is skipped when its input file has no missing
translations, or when its output file already exists and is complete. Nothing
is overwritten in place; each completed book is written to a ``.partial`` file
and atomically renamed, so a crash never corrupts a finished book and a
re-run only does the missing work (no API quota is spent on finished cards).

Usage::

    python -m book_to_flashcards.translate_books \
        --input path/to/site/api/books/ru --output data/translations-site \
        --workers 4 [--only-author "Имя Автора"] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from book_to_flashcards.Card import Card
from book_to_flashcards.cards_jsonl import cards_from_jsonl_file
from book_to_flashcards.opencode_translator import OpenCodeGoError, OpenCodeGoTranslator
from book_to_flashcards.translate_cards import translate_cards

logger = logging.getLogger("translate_books")

HOLE_ATTEMPTS = 3
REPAIR_ROUNDS = 4
MIN_SOURCE_LEN = 40
MIN_RATIO = 0.6


def suspect_card(card: Card) -> bool:
    """True if the translation is suspiciously short for its source.

    The translation model sometimes emits a 'compressed' response that covers
    only the first sentence/line of each card, while still being valid JSON.
    Such translations are short relative to the source; full translations
    typically run 0.9-1.4x the source length, compressed ones ~0.3x. Cards
    with very short sources are exempt (ratio is noise there).
    """
    text = card.text or ""
    translation = card.translation or ""
    return len(text) >= MIN_SOURCE_LEN and bool(translation) and len(translation) < MIN_RATIO * len(text)


def card_to_line(card: Card) -> str:
    """Compact, raw-UTF-8 jsonl line, matching the corpus format exactly."""
    return json.dumps(card.__dict__, ensure_ascii=False, separators=(",", ":"))


def missing_indices(cards) -> list[int]:
    return [i for i, card in enumerate(cards) if not card.translation]


def translate_book(cards, translator: OpenCodeGoTranslator, lang: str):
    """Translate every card of one book, retrying holes individually.

    The main pass is the batch machinery from ``translate_cards`` (60-card
    batches, preceding-text context). Any cards that still come back with an
    empty translation -- the model is allowed to return "" for a fragment,
    and split recovery gives up at small batch sizes -- are then retried one
    at a time, with the previous card's text as context, for a few rounds.

    Returns (translated_cards, all_present: bool).
    """
    translated = list(translate_cards(cards, translator, lang))
    for _ in range(HOLE_ATTEMPTS):
        holes = missing_indices(translated)
        if not holes:
            break
        for i in holes:
            context = translated[i - 1].text if i > 0 else ""
            try:
                result = translator.translate_cards([translated[i]], lang, context)
                translated[i].translation = result[0]
            except (OpenCodeGoError, TypeError, ValueError):
                pass  # try again next round

    # Compression repair: the model intermittently answers a whole call in
    # 'compressed mode' (every card gets a first-line-only translation, still
    # valid JSON). Because the mode is per call, re-translate all suspect
    # cards of the book together each round and keep the longest translation
    # seen. A book only counts as complete when no card is suspect.
    for _ in range(REPAIR_ROUNDS):
        suspects = [i for i, card in enumerate(translated) if suspect_card(card)]
        if not suspects:
            break
        batch = [translated[i] for i in suspects]
        context = translated[suspects[0] - 1].text if suspects[0] > 0 else ""
        try:
            results = translator.translate_cards(batch, lang, context)
            for i, tr in zip(suspects, results):
                if len(tr) > len(translated[i].translation):
                    translated[i].translation = tr
        except (OpenCodeGoError, TypeError, ValueError):
            pass  # try again next round

    complete = not missing_indices(translated) and not any(suspect_card(c) for c in translated)
    return translated, complete


def process_book(src: Path, out: Path, translator: OpenCodeGoTranslator, lang: str, fresh: bool = False):
    """Translate one book file; returns (status, cards_written).

    With ``fresh``, existing translations in the input are ignored and every
    card is re-translated (used to redo books produced by unverified runs).
    """
    def complete_set(cs) -> bool:
        return bool(cs) and not missing_indices(cs) and not any(suspect_card(c) for c in cs)

    first_line = next((l for l in src.read_text(encoding="utf-8").splitlines() if l.strip()), "")
    if first_line.startswith('{"filename"'):
        # stale pre-Card-schema file (filename/index_in_file); the site never
        # serves these, and every one we've seen has a new-schema sibling.
        logger.info("skipped %s: old schema, stale", src.name)
        return "skipped", 0

    if fresh:
        cards = list(cards_from_jsonl_file(src))
        if not cards:
            return "empty-input", 0
        for card in cards:
            card.translation = ""
    elif out.exists() and out.stat().st_size > 0:
        # Reuse the previous output when present: good translations are kept,
        # only empty or compressed cards are redone. This also repairs books
        # written by earlier runs that predate the compression check.
        cards = list(cards_from_jsonl_file(out))
        if complete_set(cards):
            return "skipped", 0
    else:
        cards = list(cards_from_jsonl_file(src))
        if not cards:
            return "empty-input", 0
        if complete_set(cards):
            return "skipped", 0

    src_count = sum(1 for _ in cards_from_jsonl_file(src))
    if len(cards) != src_count:
        logger.error("%s: card count changed %d -> %d", src, src_count, len(cards))
        return "failed", 0

    t0 = time.time()
    translated, complete = translate_book(cards, translator, lang)
    if not complete:
        holes = len(missing_indices(translated))
        suspects = sum(1 for c in translated if suspect_card(c))
        logger.error(
            "%s: %d holes, %d compressed after %d repair rounds",
            src, holes, suspects, REPAIR_ROUNDS,
        )
        return "failed", 0
    if len(translated) != len(cards):
        logger.error("%s: card count changed %d -> %d", src, len(cards), len(translated))
        return "failed", 0

    out.parent.mkdir(parents=True, exist_ok=True)
    partial = out.with_name(out.name + ".partial")
    with open(partial, "w", encoding="utf-8") as fh:
        fh.writelines(card_to_line(card) + "\n" for card in translated)
    os.replace(partial, out)
    logger.info("ok %s: %d cards in %.0fs", src.name, len(cards), time.time() - t0)
    return "ok", len(cards)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="folder of per-book jsonl files")
    ap.add_argument("--output", required=True, help="staging folder to write translated books")
    ap.add_argument("--workers", type=int, default=4, help="parallel worker threads (default 4)")
    ap.add_argument("--lang", default="English", help="language to translate into")
    ap.add_argument("--model", default="deepseek-v4-flash", help="OpenCode Go model")
    ap.add_argument("--only-author", default="", help="restrict to one author subfolder")
    ap.add_argument("--fresh", action="store_true", help="re-translate every card, ignoring existing translations in the input")
    ap.add_argument("--limit", type=int, default=0, help="process at most this many books (0 = all)")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    inp = Path(args.input)
    out = Path(args.output)
    jobs = []
    for f in sorted(inp.glob("*/*.jsonl")):
        if args.only_author and f.parent.name != args.only_author:
            continue
        jobs.append((f, out / f.relative_to(inp)))
    if args.limit:
        jobs = jobs[: args.limit]

    translator = OpenCodeGoTranslator(model=args.model)
    logger.info(
        "translating %d books (%s -> %s) with %d workers",
        len(jobs), args.lang, args.model, args.workers,
    )

    stats = {"ok": 0, "skipped": 0, "failed": 0, "crashed": 0, "empty-input": 0}
    cards_done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_book, src, dst, translator, args.lang, args.fresh): src
            for src, dst in jobs
        }
        for fut in as_completed(futures):
            src = futures[fut]
            try:
                status, n = fut.result()
            except Exception:  # one bad book must never kill the pool
                logger.exception("book %s crashed", src)
                status, n = "crashed", 0
            stats[status] = stats.get(status, 0) + 1
            cards_done += n

    logger.info("finished: %s, %d cards translated in %.0fs", stats, cards_done, time.time() - t0)
    return 1 if stats.get("failed") or stats.get("crashed") else 0


if __name__ == "__main__":
    sys.exit(main())
