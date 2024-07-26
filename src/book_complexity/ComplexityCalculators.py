from dataclasses import dataclass
from typing import Callable
from spacy.tokens import Token, Doc, Span


def word_count(doc: Doc):
    return sum(1 for token in doc if not token.is_punct and not token.is_space)


def sentence_count(doc: Doc) -> int:
    return sum(1 for dummy in doc.sents)


def cumulative_word_length(doc: Doc) -> int:
    return sum(
        len(token.text) for token in doc if not token.is_punct and not token.is_space
    )


def __grammar_depth(root_token: Token):
    """The depth of the grammatical tree, starting with root_token as the root of the tree"""

    return 1 + max((__grammar_depth(child) for child in root_token.children), default=0)


def __sentence_grammar_depth(sent: Span) -> int:
    roots = [token for token in sent if token.dep_ == "ROOT"]
    assert len(roots) == 1
    return __grammar_depth(roots[0])


def cumulative_grammar_depth(doc: Doc) -> int:
    return sum(__sentence_grammar_depth(sent) for sent in doc.sents)


def words_known(doc: Doc, vocabulary: set[str]) -> int:
    return sum(1 for token in doc if ((token.text in vocabulary) or token.is_digit))


def __token_level(token: Token, frequency: dict[str, int], levels: list[range]) -> int:
    "Return the correct vocabulary level that reflects the frequency of this token"

    token_frequency = frequency.get(token.text.lower(), 0)
    return next(
        (i for i, range in enumerate(levels) if token_frequency in range),
        0,
    )


def vocabulary_level(doc: Doc, frequency: dict[str, int], levels: list[range]) -> int:
    # what is the vocab level of this doc?
    # let's say it's the level where all the vocab in the doc is at or below the level
    return max((__token_level(token, frequency, levels) for token in doc), default=0)


def add(x, y) -> int:
    return x + y


@dataclass
class ComplexityCalculator:
    get_value: Callable[[Doc], int]
    combine_values: Callable[[int, int], int] = add
