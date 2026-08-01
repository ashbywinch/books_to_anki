"""Card translation orchestration.

Cards are translated in batches so we don't need a round trip per card, but
with a twist: batches never mix books, and each batch is translated in the
context of the text that immediately precedes it in its book. That context is
what lets the model resolve pronouns, references, and register correctly when
a card starts mid-sentence.
"""

from collections.abc import Generator, Sequence

from .Card import Card


class Translator:
    """Interface for card translators.

    A translator takes a list of cards (all from the same book, in reading
    order) plus the text that precedes them in that book, and returns one
    translation per card. ``translate_text`` keeps the old string-based
    interface used by the dummy translator and by tests.
    """

    batch_size = 200

    def translate_text(self, text, target_lang):
        """Translate a single string or a list of strings.

        Matches the DeepL-style translator interface (string or list of
        strings in, same shape out), so simple translators can be tested
        without going through the card machinery.
        """
        raise NotImplementedError

    def translate_cards(
        self, cards: Sequence[Card], lang: str, context: str = ""
    ) -> list[str]:
        """Return one translation per card, in order.

        ``context`` is the text of the book immediately preceding ``cards``.
        """
        translations = self.translate_text([card.text for card in cards], target_lang=lang)
        return [str(t) for t in translations]

class ReverseTextTranslator(Translator):
    """A trivial 'translator' for use in testing, that just reverses the text in each string"""

    def translate_text(self, text, target_lang):
        """Match the DeepL-style translator interface,
        which can handle individual strings or lists of strings
        and takes a target language, which we ignore here"""
        if isinstance(text, str):
            return text[::-1]  # just reverse the text, easy to verify in tests
        else:  # it's a list of strings
            return [s[::-1] for s in text]


def _translate_batch(
    cards: Sequence[Card],
    translator: Translator,
    lang: str,
    context: str,
) -> Generator[Card, None, None]:
    """Translate one batch of same-book cards and yield them with translations.

    Only cards that do not already have a translation are sent to the
    translator, so re-running translation on an already-translated jsonl is a
    no-op (and never uses up any API quota). Cards whose text is
    whitespace-only have nothing to translate: they are marked with their own
    text as the translation so the model never sees them (the model reliably
    drops empty fragments, which broke the index-completeness check).
    """
    for card in cards:
        if not card.translation and not card.text.strip():
            card.translation = card.text
    missing = [card for card in cards if not card.translation]
    if not missing:
        yield from cards
        return
    translations = translator.translate_cards(missing, lang, context)
    it = iter(translations)
    for card in cards:
        if card.translation:
            yield card
        else:
            card.translation = str(next(it))
            yield card


def translate_cards(
    cards, translator: Translator, lang: str, context_cards: int = 10
) -> Generator[Card, None, None]:
    """Yield all the incoming cards but with translations added.

    Cards are grouped by book (title + author) and translated in batches of
    ``translator.batch_size``. Each batch is translated with the text of the
    previous ``context_cards`` cards of the same book prepended as context, so
    translations are consistent with the larger work. Books are never mixed
    within a batch, because context must not leak across book boundaries.
    """
    pending: list[Card] = []
    current_book = None
    seen: list[str] = []  # texts of the last `context_cards` cards of the current book

    def flush() -> Generator[Card, None, None]:
        nonlocal pending, seen
        if not pending:
            return
        batch, pending = pending, []
        context = "".join(seen)
        yield from _translate_batch(batch, translator, lang, context)
        seen.extend(card.text for card in batch)
        del seen[:-context_cards]

    for card in cards:
        book = (card.title, card.author)
        if book != current_book:
            yield from flush()
            current_book = book
            seen = []
        pending.append(card)
        if len(pending) >= translator.batch_size:
            yield from flush()
    yield from flush()
