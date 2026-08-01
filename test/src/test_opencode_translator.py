"""Tests for the OpenCode Go translator and context-aware card translation."""

import json
import urllib.error

import pytest  # type: ignore

from book_to_flashcards.Card import Card
from book_to_flashcards.opencode_translator import (
    OpenCodeGoError,
    OpenCodeGoTranslator,
    find_api_key,
    parse_translation_response,
)
from book_to_flashcards.translate_cards import Translator, translate_cards


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


class RecordingTranslator(Translator):
    """Records (texts, context, lang) per call and returns trivial translations."""

    batch_size = 5

    def __init__(self):
        self.calls = []

    def translate_cards(self, cards, lang, context=""):
        self.calls.append(([c.text for c in cards], context, lang))
        return [f"T{i}" for i in range(1, len(cards) + 1)]


class TestContextAwareBatching:
    def test_batches_never_mix_books(self):
        translator = RecordingTranslator()
        cards = make_cards("book1", 12) + make_cards("book2", 3)
        out = list(translate_cards(cards, translator, "English"))
        assert len(out) == 15
        assert len(translator.calls) == 4
        # every call's texts belong to a single book
        for texts, _, _ in translator.calls:
            books = {t.split(" ")[0] for t in texts}
            assert len(books) == 1

    def test_batch_sizes_and_book_flush(self):
        translator = RecordingTranslator()
        cards = make_cards("book1", 12) + make_cards("book2", 3)
        list(translate_cards(cards, translator, "English"))
        sizes = [len(texts) for texts, _, _ in translator.calls]
        assert sizes == [5, 5, 2, 3]  # book1: 5,5,2 then book2 flushed at change

    def test_context_is_preceding_text(self):
        translator = RecordingTranslator()
        cards = make_cards("book1", 7)
        list(translate_cards(cards, translator, "English"))
        first_texts, first_context, lang = translator.calls[0]
        assert first_context == ""
        assert lang == "English"
        _, second_context, _ = translator.calls[1]
        assert second_context == "".join(first_texts)

    def test_context_resets_between_books(self):
        translator = RecordingTranslator()
        cards = make_cards("book1", 6) + make_cards("book2", 3)
        list(translate_cards(cards, translator, "English"))
        _, book2_context, _ = translator.calls[-1]
        assert book2_context == ""

    def test_already_translated_batch_is_skipped(self):
        translator = RecordingTranslator()
        cards = make_cards("book1", 3)
        for card in cards:
            card.translation = "done"
        out = list(translate_cards(cards, translator, "English"))
        assert translator.calls == []
        assert all(card.translation == "done" for card in out)

    def test_only_untranslated_cards_are_sent(self):
        translator = RecordingTranslator()
        cards = make_cards("book1", 4)
        cards[1].translation = "already"
        cards[3].translation = "done"
        out = list(translate_cards(cards, translator, "English"))
        # only the two untranslated cards were sent, in order
        assert len(translator.calls) == 1
        texts, _, _ = translator.calls[0]
        assert texts == ["book1 0", "book1 2"]
        # and the already-translated ones were kept as-is
        assert out[1].translation == "already"
        assert out[3].translation == "done"
        assert out[0].translation == "T1"
        assert out[2].translation == "T2"

    def test_context_cards_limits_context_length(self):
        translator = RecordingTranslator()
        cards = make_cards("book1", 12)
        list(translate_cards(cards, translator, "English", context_cards=2))
        _, third_context, _ = translator.calls[2]
        # only the last 2 texts of the previous batch are kept
        assert third_context == "book1 8book1 9"


class TestParseTranslationResponse:
    def test_plain_array(self):
        assert parse_translation_response(
            '[{"index":1,"source":"X","translation":"A"}]', 1
        ) == [(1, ("X", "A"))]

    def test_markdown_fences(self):
        assert parse_translation_response(
            '```json\n[{"index":1,"source":"X","translation":"A"}]\n```', 1
        ) == [(1, ("X", "A"))]

    def test_prose_around_json(self):
        assert parse_translation_response(
            'Sure! Here it is:\n[{"index":1,"source":"X","translation":"A"}]\nHope that helps', 1
        ) == [(1, ("X", "A"))]

    def test_missing_index(self):
        with pytest.raises(ValueError):
            parse_translation_response('[{"index":1,"source":"X","translation":"A"}]', 2)

    def test_duplicate_index(self):
        with pytest.raises(ValueError):
            parse_translation_response(
                '[{"index":1,"source":"X","translation":"A"},{"index":1,"source":"Y","translation":"B"}]', 2
            )

    def test_not_json(self):
        with pytest.raises(ValueError):
            parse_translation_response("no translations here", 1)

    def test_malformed_entry(self):
        with pytest.raises(TypeError):
            parse_translation_response('[{"index":1}]', 1)


class FakeResponse:
    def __init__(self, payload):
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._data


def completion(content):
    return {"choices": [{"message": {"content": content}}]}


def make_fake_urlopen(responses):
    calls = []

    def urlopen(request, timeout=None):
        calls.append(request)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)

    return urlopen, calls


def make_translator(responses):
    urlopen, calls = make_fake_urlopen(responses)
    translator = OpenCodeGoTranslator(api_key="test-key", urlopen=urlopen)
    return translator, calls


class TestOpenCodeGoTranslator:
    def test_translates_cards_in_order(self):
        translator, calls = make_translator(
            [
                completion(
                    '[{"index":1,"source":"book 0","translation":"one"},{"index":2,"source":"book 1","translation":"two"},{"index":3,"source":"book 2","translation":"three"}]'
                )
            ]
        )
        cards = make_cards("book", 3)
        translations = translator.translate_cards(cards, "English", context="CTX")
        assert translations == ["one", "two", "three"]

        # the request carried the model, the book info and the context
        payload = json.loads(calls[0].data)
        assert payload["model"] == "deepseek-v4-flash"
        system = payload["messages"][0]["content"]
        user = payload["messages"][1]["content"]
        assert "book" in system
        assert "CTX" in user
        assert "[1] book 0" in user

    def test_reordered_indices_are_resorted(self):
        translator, _ = make_translator(
            [
                completion(
                    '[{"index":3,"source":"book 2","translation":"three"},{"index":1,"source":"book 0","translation":"one"},{"index":2,"source":"book 1","translation":"two"}]'
                )
            ]
        )
        cards = make_cards("book", 3)
        assert translator.translate_cards(cards, "English", "") == [
            "one",
            "two",
            "three",
        ]

    def test_misaligned_source_is_rejected(self):
        # the model paired a translation with the wrong fragment: the echoed
        # source does not match its card, so the batch is rejected. With two
        # cards there is real alignment to protect.
        translator, _ = make_translator(
            [
                completion(
                    '[{"index":1,"source":"book 0","translation":"one"},{"index":2,"source":"totally different","translation":"two"}]'
                ),
                completion(
                    '[{"index":1,"source":"book 0","translation":"one"},{"index":2,"source":"totally different","translation":"two"}]'
                ),
            ]
        )
        cards = make_cards("book", 2)
        with pytest.raises(ValueError):
            translator.translate_cards(cards, "English", "")

    def test_single_card_skips_alignment_check(self):
        # with one card there is nothing to shift against; the echo check is
        # skipped so a sloppy echo cannot strand the book at the deepest split
        translator, _ = make_translator(
            [
                completion('[{"index":1,"source":"nonsense","translation":"one"}]')
            ]
        )
        cards = make_cards("book", 1)
        assert translator.translate_cards(cards, "English", "") == ["one"]

    def test_echo_with_list_numbering_prefix_passes(self):
        # the model sometimes echoes the prompt's "[N] " numbering before the
        # fragment text; the check must tolerate it (observed in production)
        card = Card(
            title="book", author="Author", start=0, end=60,
            text="(1598 года, 20 февраля",
        )
        translator, _ = make_translator(
            [
                completion(
                    '[{"index":1,"source":"[1] (1598 года, 20 ф","translation":"one"}]'
                )
            ]
        )
        assert translator.translate_cards([card], "English", "") == ["one"]

    def test_echo_with_small_transcription_variant_passes(self):
        # the model sometimes echoes a character differently while still
        # echoing the right fragment ("сестрою" vs "сестрой", observed in
        # production); an exact-prefix check looped forever on this
        card = Card(
            title="book", author="Author", start=0, end=60,
            text="С сестрой своею Дашей, тоже воспитанницей Варвары Петровны",
        )
        translator, _ = make_translator(
            [
                completion(
                    '[{"index":1,"source":"С сестрою своею Дашей, тоже воспитанницей","translation":"one"}]'
                )
            ]
        )
        assert translator.translate_cards([card], "English", "") == ["one"]

    def test_bare_object_stream_is_parsed(self):
        # the model sometimes omits the array wrapper entirely
        translator, _ = make_translator(
            [
                completion(
                    '{"index":1,"source":"book 0","translation":"one"}\n'
                    '{"index":2,"source":"book 1","translation":"two"}'
                )
            ]
        )
        cards = make_cards("book", 2)
        assert translator.translate_cards(cards, "English", "") == ["one", "two"]

    def test_bad_batch_is_split_into_halves(self):
        # whole batch fails twice, then each half succeeds
        translator, calls = make_translator(
            [
                completion("Sorry, I cannot answer that."),
                completion("Still no translations."),
                completion('[{"index":1,"source":"book 0","translation":"one"}]'),
                completion('[{"index":1,"source":"book 1","translation":"two"}]'),
            ]
        )
        cards = make_cards("book", 2)
        assert translator.translate_cards(cards, "English", "") == [
            "one",
            "two",
        ]
        assert len(calls) == 4

    def test_split_halves_inherit_preceding_text_as_context(self):
        # whole batch fails twice, then the second half fails twice more:
        # every split must carry the text that precedes it as context, so
        # split cards keep the surrounding text for pronouns and references
        translator, calls = make_translator(
            [
                completion("bad"),
                completion("bad"),
                completion(
                    '[{"index":1,"source":"book 0","translation":"one"},{"index":2,"source":"book 1","translation":"two"}]'
                ),
                completion("bad"),
                completion("bad"),
                completion('[{"index":1,"source":"book 2","translation":"three"}]'),
                completion('[{"index":1,"source":"book 3","translation":"four"}]'),
            ]
        )
        cards = make_cards("book", 4)
        assert translator.translate_cards(cards, "English", "") == [
            "one",
            "two",
            "three",
            "four",
        ]
        users = [json.loads(c.data)["messages"][1]["content"] for c in calls]
        assert len(users) == 7
        # the [b2, b3] call and the [b2] call inherit the first half's text
        assert "book 0book 1" in users[3]
        assert "book 0book 1" in users[5]
        # the single-card [b3] call also inherits b2's text
        assert "book 0book 1book 2" in users[6]

    def test_single_bad_card_raises(self):
        translator, _ = make_translator(
            [
                completion("nope"),
                completion("nope"),
            ]
        )
        cards = make_cards("book", 1)
        with pytest.raises(ValueError):
            translator.translate_cards(cards, "English", "")

    def test_empty_content_raises_opencode_error(self):
        translator, calls = make_translator(
            [
                completion(""),
                completion(""),
            ]
        )
        cards = make_cards("book", 1)
        with pytest.raises(OpenCodeGoError):
            translator.translate_cards(cards, "English", "")
        assert len(calls) == 2  # whole-batch retry happened

    def test_http_error_raises_opencode_error(self):
        import io

        error = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {}, io.BytesIO(b"rate limited")
        )

        def urlopen(request, timeout=None):
            raise error

        translator = OpenCodeGoTranslator(api_key="test-key", urlopen=urlopen)
        cards = make_cards("book", 1)
        with pytest.raises(OpenCodeGoError):
            translator.translate_cards(cards, "English", "")


class TestFindApiKey:
    def test_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_API_KEY", "env-key")
        assert find_api_key() == "env-key"

    def test_missing_key_raises(self, monkeypatch):
        from pathlib import Path

        monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setattr(Path, "home", lambda: Path("/nonexistent"))
        with pytest.raises(OpenCodeGoError):
            find_api_key()
