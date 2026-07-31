"""Tests for the parallel book translation driver."""

from __future__ import annotations

import json

from book_to_flashcards.Card import Card
from book_to_flashcards.translate_books import (
    card_to_line,
    missing_indices,
    process_book,
    suspect_card,
    translate_book,
)


def make_cards(book: str, n: int, text: str | None = None) -> list[Card]:
    return [
        Card(
            title=book,
            author="Author",
            start=i * 10,
            end=i * 10 + 5,
            text=text or f"{book} {i}",
        )
        for i in range(n)
    ]


def long_text_cards(book: str, n: int) -> list[Card]:
    """Cards with substantial multi-line text (longer than MIN_SOURCE_LEN)."""
    body = "Одна длинная строка текста для перевода, а затем ещё одна строка.\nИ вторая строка с продолжением."
    return make_cards(book, n, text=body)


class FakeTranslator:
    """Returns scripted translations; records the texts it was asked to translate."""

    batch_size = 60

    def __init__(self, responses):
        self.responses = list(responses)  # one response per translate_cards call
        self.calls = []

    def translate_cards(self, cards, lang, context=""):
        self.calls.append([c.text for c in cards])
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return [response(c) for c in cards]


class TestCardToLine:
    def test_compact_format_with_raw_utf8(self):
        line = card_to_line(make_cards("Книга", 1)[0])
        assert json.loads(line) == {
            "title": "Книга",
            "author": "Author",
            "start": 0,
            "end": 5,
            "text": "Книга 0",
            "translation": "",
        }
        # compact separators, no spaces after colons
        assert ": " not in line


class TestMissingIndices:
    def test_finds_empty_translations(self):
        cards = make_cards("b", 3)
        cards[1].translation = "done"
        assert missing_indices(cards) == [0, 2]


class TestSuspectCard:
    def test_short_translation_is_suspect(self):
        card = Card(title="t", author="a", start=0, end=10, text="x" * 100, translation="y" * 30)
        assert suspect_card(card)

    def test_full_translation_not_suspect(self):
        card = Card(title="t", author="a", start=0, end=10, text="x" * 100, translation="y" * 80)
        assert not suspect_card(card)

    def test_short_source_exempt(self):
        card = Card(title="t", author="a", start=0, end=10, text="x" * 20, translation="y")
        assert not suspect_card(card)

    def test_empty_translation_not_suspect(self):
        # holes are the hole-fill pass's job, not the compression check's
        card = Card(title="t", author="a", start=0, end=10, text="x" * 100, translation="")
        assert not suspect_card(card)


class TestTranslateBook:
    def test_holes_are_retried_individually(self):
        cards = long_text_cards("b", 3)
        full = lambda c: "FULL: " + c.text
        # first batch call returns a hole for card 1; the per-card retry fills it
        translator = FakeTranslator(
            [lambda c: "" if c is cards[1] else f"T: {c.text}", full]
        )
        translated, complete = translate_book(cards, translator, "English")
        assert complete
        assert all(c.translation for c in translated)
        # hole retry was a single-card call
        assert len(translator.calls) == 2
        assert len(translator.calls[1]) == 1

    def test_compressed_translations_are_repaired(self):
        cards = long_text_cards("b", 4)
        full = lambda c: "FULL TRANSLATION " + c.text
        short = lambda c: "short"
        # first two calls are compressed-mode (whole batch + retry), then full
        translator = FakeTranslator([short, short, full])
        translated, complete = translate_book(cards, translator, "English")
        assert complete
        assert all(len(c.translation) > len("short") for c in translated)

    def test_persistently_compressed_book_fails(self):
        cards = long_text_cards("b", 2)
        short = lambda c: "short"
        translator = FakeTranslator([short] * 10)
        _, complete = translate_book(cards, translator, "English")
        assert not complete

    def test_already_translated_cards_are_not_resent(self):
        cards = long_text_cards("b", 3)
        for card in cards:
            card.translation = "already fully translated " * 4
        translator = FakeTranslator([])
        _, complete = translate_book(cards, translator, "English")
        assert complete
        assert translator.calls == []


class TestProcessBook:
    def test_skips_complete_existing_output(self, tmp_path):
        src = tmp_path / "src" / "Author" / "book.jsonl"
        src.parent.mkdir(parents=True)
        cards = long_text_cards("book", 2)
        for card in cards:
            card.translation = "fully translated " * 4
        src.write_text("\n".join(card_to_line(c) for c in cards) + "\n", encoding="utf-8")
        out = tmp_path / "out" / "Author" / "book.jsonl"
        out.parent.mkdir(parents=True)
        out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

        translator = FakeTranslator([])
        status, n = process_book(src, out, translator, "English")
        assert status == "skipped"
        assert n == 0
        assert translator.calls == []

    def test_fresh_ignores_existing_translations(self, tmp_path):
        src = tmp_path / "src" / "Author" / "book.jsonl"
        src.parent.mkdir(parents=True)
        cards = long_text_cards("book", 2)
        for card in cards:
            card.translation = "old but fully translated " * 4
        src.write_text("\n".join(card_to_line(c) for c in cards) + "\n", encoding="utf-8")
        out = tmp_path / "out" / "Author" / "book.jsonl"

        translator = FakeTranslator([lambda c: f"new: {c.text}"])
        status, n = process_book(src, out, translator, "English", fresh=True)
        assert status == "ok"
        assert n == 2
        # the old translations were discarded and everything re-translated
        assert [c.text for c in cards] == translator.calls[0]

    def test_old_schema_file_is_skipped(self, tmp_path):
        src = tmp_path / "src" / "Author" / "book.jsonl"
        src.parent.mkdir(parents=True)
        src.write_text(
            '{"filename":"books/Author/book.txt","index_in_file":0,"text":"x","translation":""}\n',
            encoding="utf-8",
        )
        out = tmp_path / "out" / "Author" / "book.jsonl"
        translator = FakeTranslator([])
        status, _ = process_book(src, out, translator, "English")
        assert status == "skipped"
        assert translator.calls == []

    def test_writes_complete_atomic_output(self, tmp_path):
        src = tmp_path / "src" / "Author" / "book.jsonl"
        src.parent.mkdir(parents=True)
        cards = long_text_cards("book", 3)
        src.write_text("\n".join(card_to_line(c) for c in cards) + "\n", encoding="utf-8")
        out = tmp_path / "out" / "Author" / "book.jsonl"

        translator = FakeTranslator([lambda c: f"T: {c.text}"])
        status, n = process_book(src, out, translator, "English")
        assert status == "ok"
        assert n == 3
        written = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert all(w["translation"].startswith("T: ") for w in written)
        # no partial file left behind
        assert not list(out.parent.glob("*.partial"))

    def test_card_count_mismatch_fails(self, tmp_path):
        src = tmp_path / "src" / "Author" / "book.jsonl"
        src.parent.mkdir(parents=True)
        src.write_text(
            "\n".join(card_to_line(c) for c in long_text_cards("book", 2)) + "\n",
            encoding="utf-8",
        )
        out = tmp_path / "out" / "Author" / "book.jsonl"
        out.parent.mkdir(parents=True)
        # stale output with the wrong card count
        out.write_text(
            "\n".join(card_to_line(c) for c in long_text_cards("book", 1)) + "\n",
            encoding="utf-8",
        )
        translator = FakeTranslator([])
        status, _ = process_book(src, out, translator, "English")
        assert status == "failed"
        assert translator.calls == []

    def test_untranslatable_book_writes_nothing(self, tmp_path):
        src = tmp_path / "src" / "Author" / "book.jsonl"
        src.parent.mkdir(parents=True)
        src.write_text(
            "\n".join(card_to_line(c) for c in long_text_cards("book", 2)) + "\n",
            encoding="utf-8",
        )
        out = tmp_path / "out" / "Author" / "book.jsonl"
        translator = FakeTranslator([lambda c: ""] * 10)
        status, _ = process_book(src, out, translator, "English")
        assert status == "failed"
        assert not out.exists()


class TestMain:
    def _make_input(self, tmp_path, n=1):
        src = tmp_path / "src" / "Author"
        src.mkdir(parents=True)
        cards = long_text_cards("book", n)
        (src / "book.jsonl").write_text(
            "\n".join(card_to_line(c) for c in cards) + "\n", encoding="utf-8"
        )
        return src.parent

    def test_main_returns_zero_when_all_ok(self, tmp_path, monkeypatch):
        from book_to_flashcards.translate_books import main

        out = tmp_path / "out"
        calls = []

        def fake_process_book(s, o, t, lang, fresh=False):
            calls.append((s.name, fresh))
            return "ok", 1

        monkeypatch.setattr(
            "book_to_flashcards.translate_books.process_book", fake_process_book
        )
        monkeypatch.setattr(
            "book_to_flashcards.translate_books.OpenCodeGoTranslator",
            lambda **kw: FakeTranslator([]),
        )
        rc = main(["--input", str(self._make_input(tmp_path)), "--output", str(out), "--workers", "2"])
        assert rc == 0
        assert len(calls) == 1
        assert calls[0][1] is False  # fresh defaults to False

    def test_main_returns_one_when_books_failed(self, tmp_path, monkeypatch):
        from book_to_flashcards.translate_books import main

        monkeypatch.setattr(
            "book_to_flashcards.translate_books.process_book",
            lambda s, o, t, lang, fresh=False: "failed",
        )
        monkeypatch.setattr(
            "book_to_flashcards.translate_books.OpenCodeGoTranslator",
            lambda **kw: FakeTranslator([]),
        )
        rc = main(["--input", str(self._make_input(tmp_path)), "--output", str(tmp_path / "out")])
        assert rc == 1

    def test_main_returns_one_when_book_crashes(self, tmp_path, monkeypatch):
        from book_to_flashcards.translate_books import main

        def boom(s, o, t, lang, fresh=False):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "book_to_flashcards.translate_books.process_book", boom
        )
        monkeypatch.setattr(
            "book_to_flashcards.translate_books.OpenCodeGoTranslator",
            lambda **kw: FakeTranslator([]),
        )
        rc = main(["--input", str(self._make_input(tmp_path)), "--output", str(tmp_path / "out")])
        assert rc == 1

    def test_main_fresh_flag_passed_through(self, tmp_path, monkeypatch):
        from book_to_flashcards.translate_books import main

        calls = []

        def fake_process_book(s, o, t, lang, fresh=False):
            calls.append(fresh)
            return "ok", 1

        monkeypatch.setattr(
            "book_to_flashcards.translate_books.process_book", fake_process_book
        )
        monkeypatch.setattr(
            "book_to_flashcards.translate_books.OpenCodeGoTranslator",
            lambda **kw: FakeTranslator([]),
        )
        rc = main(
            ["--input", str(self._make_input(tmp_path)), "--output", str(tmp_path / "out"), "--fresh"]
        )
        assert rc == 0
        assert calls == [True]

    def test_main_only_author_and_limit_filters(self, tmp_path, monkeypatch):
        from book_to_flashcards.translate_books import main

        src = tmp_path / "src"
        for author in ("AuthorA", "AuthorB"):
            d = src / author
            d.mkdir(parents=True)
            (d / "book.jsonl").write_text(
                "\n".join(card_to_line(c) for c in long_text_cards("book", 1)) + "\n",
                encoding="utf-8",
            )
        seen = []

        def fake_process_book(s, o, t, lang, fresh=False):
            seen.append(s.parent.name)
            return "ok", 1

        monkeypatch.setattr(
            "book_to_flashcards.translate_books.process_book", fake_process_book
        )
        monkeypatch.setattr(
            "book_to_flashcards.translate_books.OpenCodeGoTranslator",
            lambda **kw: FakeTranslator([]),
        )
        rc = main(
            ["--input", str(src), "--output", str(tmp_path / "out"), "--only-author", "AuthorB"]
        )
        assert rc == 0
        assert seen == ["AuthorB"]
