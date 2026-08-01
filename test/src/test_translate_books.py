"""Tests for the parallel book translation driver."""

import json

from book_to_flashcards.Card import Card
from book_to_flashcards.opencode_translator import OpenCodeGoError
from book_to_flashcards.translate_books import (
    card_to_line,
    main,
    missing_indices,
    process_book,
    translate_book,
)
from book_to_flashcards.translate_cards import Translator


def make_cards(book: str, n: int, author: str = "Author") -> list[Card]:
    return [
        Card(
            title=book,
            author=author,
            start=i * 10,
            end=i * 10 + 5,
            text=f"{book} {i}",
        )
        for i in range(n)
    ]


class ScriptedTranslator(Translator):
    """Pops scripted responses per call; records (texts, context, lang).

    A response is a list of translations (one per card in the call) or an
    exception to raise. When the queue is exhausted, returns T1..Tn so a test
    can script only the calls it cares about.
    """

    batch_size = 60

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def translate_cards(self, cards, lang, context=""):
        self.calls.append(([c.text for c in cards], context, lang))
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return [f"T{i}" for i in range(1, len(cards) + 1)]


class EmptyTranslator(Translator):
    """Always returns empty translations — a model that never translates."""

    batch_size = 60

    def __init__(self):
        self.calls = []

    def translate_cards(self, cards, lang, context=""):
        self.calls.append(([c.text for c in cards], context, lang))
        return ["" for _ in cards]


class TestCardToLine:
    def test_compact_json_line_without_spaces(self):
        line = card_to_line(make_cards("book", 1)[0])
        assert line == (
            '{"title":"book","author":"Author","start":0,"end":5,'
            '"text":"book 0","translation":""}'
        )

    def test_keeps_unicode_raw(self):
        card = make_cards("книга", 1, author="Автор")[0]
        line = card_to_line(card)
        assert '"title":"книга"' in line
        assert '"author":"Автор"' in line
        # round-trips through json
        assert json.loads(line)["title"] == "книга"


class TestMissingIndices:
    def test_flags_only_untranslated_cards(self):
        cards = make_cards("book", 3)
        cards[1].translation = "done"
        assert missing_indices(cards) == [0, 2]

    def test_all_translated_is_empty(self):
        cards = make_cards("book", 2)
        for card in cards:
            card.translation = "done"
        assert missing_indices(cards) == []


class TestTranslateBook:
    def test_returns_translated_cards_when_batch_succeeds(self):
        translator = ScriptedTranslator(["T1", "T2", "T3"])
        cards = make_cards("book", 3)
        translated, complete = translate_book(cards, translator, "English")
        assert complete is True
        assert [c.translation for c in translated] == ["T1", "T2", "T3"]

    def test_hole_is_retried_individually_with_previous_card_context(self):
        # batch pass leaves card 0 empty; the per-card retry fills it
        translator = ScriptedTranslator(["", "T2", "T3"], ["T0"])
        cards = make_cards("book", 3)
        translated, complete = translate_book(cards, translator, "English")
        assert complete is True
        assert [c.translation for c in translated] == ["T0", "T2", "T3"]
        # individual retry carried the previous card's text as context
        assert translator.calls[1] == (["book 0"], "", "English")

    def test_persistent_hole_is_retried_three_rounds_then_reported(self):
        translator = EmptyTranslator()
        cards = make_cards("book", 2)
        translated, complete = translate_book(cards, translator, "English")
        assert complete is False
        assert [c.translation for c in translated] == ["", ""]
        # 1 batch call + 3 rounds x 2 holes
        assert len(translator.calls) == 7

    def test_exception_during_hole_retry_is_swallowed(self):
        # batch leaves a hole at 0; the first individual retry raises, the
        # next round retries it and fills it — the driver must not crash
        translator = ScriptedTranslator(["", "T2"], OpenCodeGoError("nope"), ["T1"])
        cards = make_cards("book", 2)
        translated, complete = translate_book(cards, translator, "English")
        assert complete is True
        assert [c.translation for c in translated] == ["T1", "T2"]
        assert len(translator.calls) == 3  # batch + failed retry + successful retry


class TestProcessBook:
    def write_book(self, path, cards):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(card_to_line(c) + "\n" for c in cards)

    def test_skips_when_output_already_complete(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        done = make_cards("book", 2)
        for card in done:
            card.translation = "done"
        self.write_book(src, done)
        self.write_book(out, done)
        translator = ScriptedTranslator()
        assert process_book(src, out, translator, "English") == ("skipped", 0)
        assert translator.calls == []

    def test_skips_stale_pre_card_schema_file(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        self.write_book(
            src,
            [Card(title="t", author="a", start=0, end=1, text="x", translation="y")],
        )
        with open(src, "w", encoding="utf-8") as fh:
            fh.write('{"filename": "old.jsonl", "index_in_file": 1}\n')
        assert process_book(src, out, ScriptedTranslator(), "English") == ("skipped", 0)

    def test_empty_input(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        self.write_book(src, [])
        assert process_book(src, out, ScriptedTranslator(), "English") == ("empty-input", 0)

    def test_skips_when_input_fully_translated(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        done = make_cards("book", 2)
        for card in done:
            card.translation = "done"
        self.write_book(src, done)
        translator = ScriptedTranslator()
        assert process_book(src, out, translator, "English") == ("skipped", 0)
        assert translator.calls == []

    def test_happy_path_writes_atomic_output(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        self.write_book(src, make_cards("book", 3))
        translator = ScriptedTranslator(["T1", "T2", "T3"])
        assert process_book(src, out, translator, "English") == ("ok", 3)
        assert out.exists()
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        assert [json.loads(l)["translation"] for l in lines] == ["T1", "T2", "T3"]
        # no .partial leftovers
        assert not out.with_name(out.name + ".partial").exists()

    def test_failed_book_writes_nothing(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        self.write_book(src, make_cards("book", 2))
        assert process_book(src, out, EmptyTranslator(), "English") == ("failed", 0)
        assert not out.exists()

    def test_interrupted_book_resumes_from_checkpoint(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        self.write_book(src, make_cards("book", 6))

        class CrashSecondBatch(ScriptedTranslator):
            batch_size = 3

            def translate_cards(self, cards, lang, context=""):
                self.calls.append(([c.text for c in cards], context, lang))
                if len(self.calls) == 2:
                    raise RuntimeError("api down")
                return [f"T{i}" for i in range(1, len(cards) + 1)]

        import pytest

        with pytest.raises(RuntimeError):
            process_book(src, out, CrashSecondBatch(), "English")
        partial = out.with_name(out.name + ".partial")
        assert partial.exists()
        done = [
            json.loads(l)["translation"]
            for l in partial.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]
        assert len(done) == 3 and all(done)  # first batch checkpointed

        # resume: only the missing tail is translated, and the checkpoint is
        # consumed into the final output
        resumer = ScriptedTranslator()
        assert process_book(src, out, resumer, "English") == ("ok", 6)
        assert not partial.exists()
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 6
        assert all(json.loads(l)["translation"] for l in lines)
        assert len(resumer.calls[0][0]) == 3  # only the tail was re-sent

    def test_stale_checkpoint_is_discarded(self, tmp_path):
        src = tmp_path / "src" / "book.jsonl"
        out = tmp_path / "out" / "book.jsonl"
        self.write_book(src, make_cards("book", 4))
        partial = out.with_name(out.name + ".partial")
        stale = make_cards("book", 4)
        for c in stale:
            c.text = "DIFFERENT TEXT"
            c.translation = "stale"
        self.write_book(partial, stale)

        translator = ScriptedTranslator(["A", "B", "C", "D"])
        assert process_book(src, out, translator, "English") == ("ok", 4)
        assert not partial.exists()
        assert [
            json.loads(l)["translation"]
            for l in out.read_text(encoding="utf-8").splitlines()
        ] == ["A", "B", "C", "D"]


class TestMain:
    def write_input_book(self, tmp_path, n=1):
        src = tmp_path / "src" / "author"
        src.mkdir(parents=True)
        with open(src / "book.jsonl", "w", encoding="utf-8") as fh:
            fh.writelines(card_to_line(c) + "\n" for c in make_cards("book", n))
        return src

    def make_factory(self, translator):
        def factory(model=None, batch_size=None):
            return translator

        return factory

    def test_main_reports_failure_exit_code(self, tmp_path):
        self.write_input_book(tmp_path)
        rc = main(
            ["--input", str(tmp_path / "src"), "--output", str(tmp_path / "out"), "--workers", "1"],
            translator_factory=self.make_factory(EmptyTranslator()),
        )
        assert rc == 1

    def test_main_succeeds_when_books_translate(self, tmp_path):
        self.write_input_book(tmp_path)
        rc = main(
            ["--input", str(tmp_path / "src"), "--output", str(tmp_path / "out"), "--workers", "1"],
            translator_factory=self.make_factory(ScriptedTranslator(["T1"])),
        )
        assert rc == 0
        out = tmp_path / "out" / "author" / "book.jsonl"
        assert out.exists()
        assert json.loads(out.read_text(encoding="utf-8").splitlines()[0])["translation"] == "T1"

    def test_main_respects_only_author_filter(self, tmp_path):
        src = tmp_path / "src"
        (src / "author1").mkdir(parents=True)
        (src / "author2").mkdir(parents=True)
        for author in ("author1", "author2"):
            with open(src / author / "book.jsonl", "w", encoding="utf-8") as fh:
                fh.writelines(card_to_line(c) + "\n" for c in make_cards("book", 1))
        rc = main(
            ["--input", str(src), "--output", str(tmp_path / "out"), "--workers", "1", "--only-author", "author2"],
            translator_factory=self.make_factory(ScriptedTranslator(["T1"])),
        )
        assert rc == 0
        assert (tmp_path / "out" / "author2" / "book.jsonl").exists()
        assert not (tmp_path / "out" / "author1" / "book.jsonl").exists()
