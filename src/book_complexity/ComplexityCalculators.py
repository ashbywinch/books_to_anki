from dataclasses import dataclass
from functools import reduce
from typing import Any, OrderedDict

from line_profiler import profile
from spacy.tokens import Doc, Token, Span


@dataclass
class ComplexityCalculator:
    """Calculate complexity either per sentence, or per token
    Results for each sentence/token can be combined with combine_values to give a score for the
    whole document.
    The final value will be processed once with and_finally
    """

    name: str = ""

    # Take a sentence and return your type of choice
    def process_sentence(self, span: Span):
        return self.null_value()

    # Take a token and return your type of choice
    def process_token(self, token: Token):
        return self.null_value()

    # Take two objects with the same type as the return type from process_token. Return the same type.
    # Used to combine values from multiple tokens/sentences to give a value for a whole doc/text
    def combine_values(self, x, y):
        return x + y

    # Take a single object with the same type as the return type from process_token. Return a number.
    # Allows subclasses to postprocess the combined values in some way
    def and_finally(self, combined_values):
        return combined_values

    # A value that we can kick off our combination efforts with
    def null_value(self):
        return 0


@dataclass
class ComplexityRatio:
    """The names of the two complexity calculator objects whose values
    we'll use in a ratio calculation"""

    name: str
    numerator: str
    denominator: str
    percentage: bool = False

    def as_percentage(self):
        return ComplexityRatio(self.name, self.numerator, self.denominator, True)


# All our calculators and results are referenced by a name e.g. "Grammar Depth"
ComplexityResults = OrderedDict[str, Any]


class ComplexityCalculators:
    """Build an ordered collection of complexity calculators and ratios.
    Use map/reduce to apply the calculators to a document (breaking the document
    down into sentences and tokens as appropriate to the calculator)
    Calculate all the ratios at the end and return all the results, in the same order as
    the original calculators and ratios were provided.
    """

    calculators = OrderedDict[str, ComplexityCalculator]()
    ratios = OrderedDict[str, ComplexityRatio]()

    def add(self, name: str, c: ComplexityCalculator):
        self.calculators[name] = c

    def addRatio(self, ratio: ComplexityRatio):
        self.ratios[ratio.name] = ratio

    def __getitem__(self, key):
        if key in self.calculators:
            return self.calculators[key]
        elif key in self.ratios:
            return self.ratios[key]
        else:
            raise Exception(f"No calculator or ratio: {key}")

    @profile
    def __get_token_values(self, token: Token) -> ComplexityResults:
        """Apply all the calculators to this token"""
        return ComplexityResults(
            [(name, c.process_token(token)) for name, c in self.calculators.items()]
        )

    @profile
    def __get_sentence_values(self, sent: Span) -> ComplexityResults:
        """Apply all the sentence calculators to this sentence,
        and the token calculators to its tokens"""

        sentence_results = ComplexityResults(
            [(name, c.process_sentence(sent)) for name, c in self.calculators.items()]
        )

        token_results = reduce(
            self.__merge, map(lambda token: self.__get_token_values(token), sent)
        )
        return self.__merge(sentence_results, token_results)

    @profile
    def __get_values(self, doc: Doc) -> ComplexityResults:
        """Apply all the calculators to this document and return the results"""
        return reduce(
            self.__merge,
            map(lambda sent: self.__get_sentence_values(sent), doc.sents),
            self.__get_initial_values(),
        )

    def __get_initial_values(self) -> ComplexityResults:
        """Null results that we would expect from an empty document"""
        return OrderedDict(
            (name, c.null_value()) for name, c in self.calculators.items()
        )

    @profile
    def __merge(self, x: ComplexityResults, y: ComplexityResults) -> ComplexityResults:
        """Call the combine_values function from each calculator on the corresponding values
        in two Results objects, resulting in one Results object
        with an accumulated result for each calculator
        """
        return ComplexityResults(
            [
                (
                    name,
                    c.combine_values(x[name], y[name]),
                )
                for name, c, in self.calculators.items()
            ]
        )

    def __get_ratio(self, ratio: ComplexityRatio, calculationResults) -> Any:
        numerator = calculationResults[ratio.numerator]
        denominator = calculationResults[ratio.denominator]
        result = numerator / denominator if denominator > 0 else 0
        return int(result * 100) if ratio.percentage else round(result, 1)

    def __get_ratios(self, calculationResults):
        return [
            [name, self.__get_ratio(ratio, calculationResults)]
            for name, ratio in self.ratios.items()
        ]

    @profile
    def get_results(self, docs) -> ComplexityResults:
        """Apply all the calculators and ratios to this doc
        and return the results"""
        results = reduce(
            lambda a, b: self.__merge(a, b),
            map(lambda doc: self.__get_values(doc), docs),
            self.__get_initial_values(),
        )
        results = self.__and_finally(results)

        for k, v in self.__get_ratios(results):
            results[k] = v

        return results

    def __and_finally(self, results: ComplexityResults):
        return ComplexityResults(
            [
                (
                    name,
                    c.and_finally(results[name]),
                )
                for name, c, in self.calculators.items()
            ]
        )


@profile
def __grammar_depth(root_token: Token):
    """The depth of the grammatical tree, starting with root_token as the root of the tree"""

    return 1 + max((__grammar_depth(child) for child in root_token.children), default=0)


@profile
def sentence_grammar_depth(sent: Span) -> int:
    roots = [token for token in sent if token.dep_ == "ROOT"]
    assert len(roots) == 1
    return __grammar_depth(roots[0])


def words_known(token: Token, vocabulary: set[str]) -> int:
    return 1 if ((token.text in vocabulary) or token.is_digit) else 0


@profile
def vocabulary_level(
    token: Token, frequency: dict[str, int], levels: list[range]
) -> int:
    "Return the correct vocabulary level that reflects the frequency of this token"

    token_frequency = frequency.get(token.text.lower(), 0)
    return next(
        (i for i, range in enumerate(levels) if token_frequency in range),
        0,
    )
