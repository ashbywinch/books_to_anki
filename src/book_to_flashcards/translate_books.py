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
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from book_to_flashcards.Card import Card
from book_to_flashcards.cards_jsonl import cards_from_jsonl_file
from book_to_flashcards.opencode_translator import OpenCodeGoError, OpenCodeGoTranslator
from book_to_flashcards.translate_cards import Translator, translate_cards

logger = logging.getLogger("translate_books")

HOLE_ATTEMPTS = 3
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "translate.config.json"


def card_to_line(card: Card) -> str:
    """Compact, raw-UTF-8 jsonl line, matching the corpus format exactly."""
    return json.dumps(card.__dict__, ensure_ascii=False, separators=(",", ":"))


def missing_indices(cards) -> list[int]:
    return [i for i, card in enumerate(cards) if not card.translation]


def translate_book(cards, translator: Translator, lang: str, checkpoint=None, checkpoint_offset=None):
    """Translate every card of one book, retrying holes individually.

    The main pass is the batch machinery from ``translate_cards`` (60-card
    batches, preceding-text context). Any cards that still come back with an
    empty translation -- the model is allowed to return "" for a fragment,
    and split recovery gives up at small batch sizes -- are then retried one
    at a time, with the previous card's text as context, for a few rounds.

    When ``checkpoint`` (a path) is given, each card is appended to it as it
    completes, so an interrupted book keeps the batches that were already
    translated and the next run resumes from them instead of redoing the
    whole book. ``checkpoint_offset`` (used when resuming) skips re-appending
    the cards that were already loaded from the checkpoint.

    Returns (translated_cards, all_present: bool).
    """
    translated = []
    if checkpoint is not None:
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
    for i, card in enumerate(translate_cards(cards, translator, lang)):
        translated.append(card)
        if checkpoint is not None and (checkpoint_offset is None or i >= checkpoint_offset):
            with open(checkpoint, "a", encoding="utf-8") as fh:
                fh.write(card_to_line(card) + "\n")
    for _ in range(HOLE_ATTEMPTS):
        holes = missing_indices(translated)
        if not holes:
            return translated, True
        for i in holes:
            context = translated[i - 1].text if i > 0 else ""
            try:
                result = translator.translate_cards([translated[i]], lang, context)
                translated[i].translation = result[0]
            except (OpenCodeGoError, TypeError, ValueError) as e:
                # a card that repeatedly fails must be visible, not silent
                logger.warning("hole card %d failed: %s", i, e)
                # try again next round
    return translated, not missing_indices(translated)


def process_book(src: Path, out: Path, translator: Translator, lang: str):
    """Translate one book file; returns (status, cards_written)."""
    if out.exists() and out.stat().st_size > 0:
        existing = list(cards_from_jsonl_file(out))
        if existing and not missing_indices(existing):
            return "skipped", 0

    first_line = next((l for l in src.read_text(encoding="utf-8").splitlines() if l.strip()), "")
    if first_line.startswith('{"filename"'):
        # stale pre-Card-schema file (filename/index_in_file); the site never
        # serves these, and every one we've seen has a new-schema sibling.
        logger.info("skipped %s: old schema, stale", src.name)
        return "skipped", 0

    cards = list(cards_from_jsonl_file(src))
    if not cards:
        return "empty-input", 0
    if not missing_indices(cards):
        return "skipped", 0

    # Resume an interrupted book from its checkpoint: the completed batches
    # are already in the .partial file; only the missing tail needs to be
    # translated. A stale checkpoint (different content, or more cards than
    # the source) is discarded and the book restarts.
    partial = out.with_name(out.name + ".partial")
    checkpoint_cards = []
    if partial.exists():
        checkpoint_cards = list(cards_from_jsonl_file(partial))
        if len(checkpoint_cards) <= len(cards) and all(
            cc.text == cards[i].text for i, cc in enumerate(checkpoint_cards)
        ):
            tail = [
                Card(
                    title=c.title, author=c.author, start=c.start, end=c.end,
                    text=c.text, translation="",
                )
                for c in cards[len(checkpoint_cards):]
            ]
            cards = checkpoint_cards + tail
            logger.info(
                "resuming %s from checkpoint (%d cards done)",
                src.name, len(checkpoint_cards),
            )
        else:
            logger.info("discarding stale checkpoint for %s", src.name)
            partial.unlink()
            checkpoint_cards = []

    t0 = time.time()
    translated, complete = translate_book(
        cards, translator, lang,
        checkpoint=partial,
        checkpoint_offset=len(checkpoint_cards) if partial.exists() else None,
    )
    if not complete:
        holes = len(missing_indices(translated))
        logger.error("%s: %d/%d cards still untranslated after retries", src, holes, len(cards))
        return "failed", 0
    if len(translated) != len(cards):
        logger.error("%s: card count changed %d -> %d", src, len(cards), len(translated))
        return "failed", 0

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(partial, "w", encoding="utf-8") as fh:
        fh.writelines(card_to_line(card) + "\n" for card in translated)
    os.replace(partial, out)
    logger.info("ok %s: %d cards in %.0fs", src.name, len(cards), time.time() - t0)
    return "ok", len(cards)


def main(
    argv: list[str] | None = None,
    translator_factory: Callable[..., Translator] | None = None,
) -> int:
    """Translate every book jsonl under --input into --output.

    ``translator_factory`` is an injection point for tests: it is called with
    ``model=...`` and must return a Translator (default: OpenCodeGoTranslator).
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="folder of per-book jsonl files")
    ap.add_argument("--output", required=True, help="staging folder to write translated books")
    ap.add_argument("--config", default=None, help=f"translation config (default: {DEFAULT_CONFIG_PATH})")
    ap.add_argument("--workers", type=int, default=None, help="parallel worker threads (default: config, else 4)")
    ap.add_argument("--batch-size", type=int, default=None, help="cards per translation API call (default: config)")
    ap.add_argument("--lang", default=None, help="language to translate into (default: config, else English)")
    ap.add_argument("--model", default=None, help="provider model id (default: config)")
    ap.add_argument("--base-url", default=None, help="OpenAI-compatible base URL (default: config)")
    ap.add_argument("--api-key-env", default=None, help="environment variable holding the API key (default: config)")
    ap.add_argument("--only-author", default="", help="restrict to one author subfolder")
    ap.add_argument("--limit", type=int, default=0, help="process at most this many books (0 = all)")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_PATH
    if args.config and not config_path.exists():
        logger.error("config file does not exist: %s", config_path)
        return 1
    try:
        config = (
            json.loads(config_path.read_text(encoding="utf-8"))
            if config_path.exists()
            else {}
        )
    except (OSError, json.JSONDecodeError) as e:
        if args.config:
            logger.error("could not read config %s: %s", config_path, e)
            return 1
        # A missing or unreadable default config is not an error: the
        # provider defaults remain usable for the legacy OpenCode path.
        config = {}
    provider = config.get("provider") or {}
    translation = config.get("translation") or {}

    base_url = args.base_url or provider.get("base_url")
    model = args.model or provider.get("model")
    api_key_env = args.api_key_env or provider.get("api_key_env")
    lang = args.lang or translation.get("lang") or "English"
    batch_size = args.batch_size if args.batch_size is not None else translation.get("batch_size")
    workers = args.workers if args.workers is not None else translation.get("workers", 4)

    inp = Path(args.input)
    out = Path(args.output)
    if not inp.is_dir():
        # fail loudly: a missing input would otherwise report success for an
        # empty run and the orchestrator/keepalive would treat it as done
        logger.error("input directory does not exist: %s", inp)
        return 1
    jobs = []
    for f in sorted(inp.glob("*/*.jsonl")):
        if args.only_author and f.parent.name != args.only_author:
            continue
        jobs.append((f, out / f.relative_to(inp)))
    if args.limit:
        jobs = jobs[: args.limit]

    if translator_factory is None:
        translator_factory = OpenCodeGoTranslator
    translator_kwargs = {
        "model": model,
        "base_url": base_url or None,
        "api_key_env": api_key_env,
        "extra_headers": provider.get("headers") or {},
        "session_header": provider.get("session_header", "x-opencode-session"),
        "json_mode": provider.get("json_mode", True),
        "disable_thinking": provider.get("disable_thinking", True),
        "temperature": provider.get("temperature", 0.0),
        "max_tokens": provider.get("max_tokens", 12000),
        "timeout": provider.get("timeout_seconds", 600.0),
        "max_retries": provider.get("max_retries", 2),
        "batch_size": batch_size,
    }
    # Omit unset provider identity fields so constructor defaults stay the
    # single source of truth; explicit nulls (e.g. session_header) are kept.
    for key in ("model", "base_url", "api_key_env", "batch_size"):
        if translator_kwargs[key] is None:
            del translator_kwargs[key]
    translator = translator_factory(**translator_kwargs)
    logger.info(
        "translating %d books (%s -> %s at %s) with %d workers",
        len(jobs), lang, model or "provider default", base_url or "provider default", workers,
    )

    stats = {"ok": 0, "skipped": 0, "failed": 0, "crashed": 0, "empty-input": 0}
    cards_done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process_book, src, dst, translator, lang): src for src, dst in jobs}
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
