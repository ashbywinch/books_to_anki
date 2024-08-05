"""Provide a substitute for DeepL so that we can stub DeepL out in testing
and therefore not require an API key"""

from itertools import chain, islice


class ReverseTextTranslator:
    """A trivial 'translator' for use in testing, that just reverses the text in each string"""

    def translate_text(self, text, target_lang):
        """Match the interface of the DeepL translator,
        which can handle individual strings or lists of strings
        and takes a target language, which we ignore here"""
        if isinstance(text, str):
            return text[::-1]  # just reverse the text, easy to verify in tests
        else:  # it's a list of strings
            return [s[::-1] for s in text]


def chunks(iterable, size=10):
    """Yield zero or more chunks of "size" items, consuming all the iterable items.
    The last chunk may be shorter than "size" """
    iterator = iter(iterable)
    for first in iterator:
        yield chain([first], islice(iterator, size - 1))


def translate_cards(cards, translator, lang):
    """Yield all the incoming cards but with translations added.
    We batch up the translations - we don't want a round trip per card.
    But we still want to be able to report progress to the user every now and then
    """

    for chunk in chunks(cards, 200):
        # get all the translations
        translations = translator.translate_text(
            [card.current for card in chunk], target_lang=lang
        )
        # put the translations back in the cards and return
        for card, translation in zip(cards, translations):
            card.translation = translation
            yield card
