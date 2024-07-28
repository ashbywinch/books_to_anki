from dataclasses import dataclass
from functools import reduce
from typing import Callable, OrderedDict

# from line_profiler import profile
from spacy.tokens import Doc, Token, Span


@dataclass
class ComplexityRatio:
    """The names of the two complexity calculator objects whose values
    we'll use in a ratio calculation"""

    numerator: str
    denominator: str
    percentage: bool = False


Number = int | float


@dataclass
class ComplexityCalculator:
    """Calculate complexity either per sentence, or per token
    Results for each sentence/token can be combined with combine_values to give a score for the
    whole document
    """

    process_sentence: Callable[[Span], Number] | None = None
    process_token: Callable[[Token], Number] | None = None
    combine_values: Callable[[Number, Number], Number] = lambda x, y: x + y


# All our calculators and results are referenced by a name e.g. "Grammar Depth"
ComplexityResults = OrderedDict[str, Number]


class ComplexityCalculators:
    """Take an ordered collection of complexity calculators and ratios.
    Use map/reduce to apply the calculators to a document (breaking the document
    down into sentences and tokens as appropriate to the calculator)
    Calculate all the ratios at the end and return all the results, in the same order as
    the original calculators and ratios were provided.
    """

    def __init__(
        self,
        calculators: OrderedDict[str, ComplexityCalculator],
        ratios: OrderedDict[str, ComplexityRatio],
    ):
        self.calculators = calculators
        self.ratios = ratios

    def __calculate_ratio(
        self, ratio: ComplexityRatio, results: ComplexityResults
    ) -> float | int:
        numerator = results[ratio.numerator]
        denominator = results[ratio.denominator]
        result = numerator / denominator if denominator > 0 else 0
        return int(result * 100) if ratio.percentage else round(result, 1)

    def __get_token_values(self, token: Token) -> ComplexityResults:
        """Apply all the calculators to this token"""
        return ComplexityResults(
            [
                (name, c.process_token(token))
                for name, c in self.calculators.items()
                if c.process_token
            ]
        )

    def __get_sentence_values(self, sent: Span) -> ComplexityResults:
        """Apply all the sentence calculators to this sentence,
        and the token calculators to its tokens"""

        sentence_results = ComplexityResults(
            [
                (name, c.process_sentence(sent))
                for name, c in self.calculators.items()
                if c.process_sentence
            ]
        )

        token_results = reduce(
            self.__merge, map(lambda token: self.__get_token_values(token), sent)
        )
        return self.__merge(sentence_results, token_results)

    def __get_values(self, doc: Doc) -> ComplexityResults:
        """Apply all the calculators to this document and return the results"""
        return reduce(
            self.__merge,
            map(lambda sent: self.__get_sentence_values(sent), doc.sents),
            self.__get_initial_values(),
        )

    def __get_initial_values(self) -> ComplexityResults:
        """Null results that we would expect from an empty document"""
        return OrderedDict((name, 0) for name, c in self.calculators.items())

    def __merge(self, x: ComplexityResults, y: ComplexityResults) -> ComplexityResults:
        """Call the combine_values function from each calculator on the corresponding values
        in two Results objects, resulting in one Results object
        with an accumulated result for each calculator
        """
        return ComplexityResults(
            [
                (name, c.combine_values(x.get(name, 0), y.get(name, 0)))
                for name, c, in self.calculators.items()
            ]
        )

    def __get_ratios(self, results: ComplexityResults):
        return [
            [name, self.__calculate_ratio(ratio, results)]
            for name, ratio in self.ratios.items()
        ]

    def get_results(self, docs) -> ComplexityResults:
        """Apply all the calculators and ratios to this doc
        and return the results"""
        results = reduce(
            lambda a, b: self.__merge(a, b),
            map(lambda doc: self.__get_values(doc), docs),
            self.__get_initial_values(),
        )
        for k, v in self.__get_ratios(results):
            results[k] = v

        return results


def word_count(token: Token):
    return 0 if token.is_punct or token.is_space else 1


def sentence_count(sentence: Span) -> int:
    return 1


def word_length(token: Token) -> int:
    return 0 if token.is_punct or token.is_space else len(token.text)


# @profile
def __grammar_depth(root_token: Token):
    """The depth of the grammatical tree, starting with root_token as the root of the tree"""

    return 1 + max((__grammar_depth(child) for child in root_token.children), default=0)


# @profile
def sentence_grammar_depth(sent: Span) -> int:
    roots = [token for token in sent if token.dep_ == "ROOT"]
    assert len(roots) == 1
    return __grammar_depth(roots[0])


def words_known(token: Token, vocabulary: set[str]) -> int:
    return 1 if ((token.text in vocabulary) or token.is_digit) else 0


# @profile
def vocabulary_level(
    token: Token, frequency: dict[str, int], levels: list[range]
) -> int:
    "Return the correct vocabulary level that reflects the frequency of this token"

    token_frequency = frequency.get(token.text.lower(), 0)
    return next(
        (i for i, range in enumerate(levels) if token_frequency in range),
        0,
    )
