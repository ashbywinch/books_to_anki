# ruff: noqa: N999  # public module name, imported as book_complexity.ComplexityCalculators
"""
Defines the core framework for calculating text complexity metrics.

This module provides:
- `ComplexityCalculator`: An abstract base class that uses map/reduce to calculate individual complexity metrics
  calculations (e.g., word count, sentence length) on a document. Subclasses should implement
  processing logic for individual tokens and/or sentences, and for combining those results into a single metric.
- `ComplexityRatio`: A dataclass to define ratios between two named
  `ComplexityCalculator` results.
- `ComplexityCalculators`: A class that manages a collection of calculators
  and ratios, applies them to spaCy `Doc` objects (or iterables of Docs),
  and aggregates the results.
- Helper functions for specific calculations like `sentence_grammar_depth`
  and `words_known`.
"""
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from functools import reduce
from typing import Any

from line_profiler import profile  # type: ignore
from spacy.tokens import Doc, Span, Token  # type: ignore


@dataclass
class ComplexityCalculator:
    """
    Abstract base class for defining a single complexity metric.

    Subclasses should override `process_sentence` and/or `process_token`
    to define how the metric is calculated for a given spaCy `Span` (sentence)
    or `Token`. A default value
    is provided by `null_value` for processors that only process sentences or only tokens. 

    The results from processing individual units (tokens/sentences) are
    aggregated using `combine_values`. A final transformation can be applied
    to the aggregated result using `and_finally`.
    """

    name: str = ""  # Name of the calculator, used as a key in results

    # Take a sentence and return your type of choice
    def process_sentence(self, span: Span) -> Any:
        """Processes a single sentence (spaCy Span) to calculate the metric.

        Args:
            span: The sentence to process.

        Returns:
            The calculated metric for this sentence. Defaults to `null_value()`.
        """
        return self.null_value()

    # Take a token and return your type of choice
    def process_token(self, token: Token) -> Any:
        """Processes a single token (spaCy Token) to calculate the metric.

        Args:
            token: The token to process.

        Returns:
            The calculated metric for this token. Defaults to `null_value()`.
        """
        return self.null_value()

    
    def combine_values(self, x: Any, y: Any) -> Any:
        """Combines two metric values.

        Used to aggregate results from multiple tokens or multiple sentences.
        Default implementation assumes numeric addition.

        Args:
            x: The first value.
            y: The second value.

        Returns:
            The combined value.
        """
        return x + y

    # Take a single object with the same type as the return type from process_token. Return a number.
    # Allows subclasses to postprocess the combined values in some way
    def and_finally(self, combined_values: Any) -> Any:
        """Applies a final transformation to the aggregated metric value for a document.

        Args:
            combined_values: The aggregated value from all processed units.

        Returns:
            The finalized metric value. Default implementation returns it unchanged.
        """
        return combined_values

    # A value that we can kick off our combination efforts with
    def null_value(self) -> Any:
        """Provides a default ('zero' or 'empty') value for the metric.

        This is used as the starting point for aggregations, 
        and for derived classes that only process tokens or only sentences.
        Default is 0, suitable for additive numeric metrics.

        Returns:
            The null/initial value for this metric.
        """
        return 0


@dataclass
class ComplexityRatio:
    """
    Dataclass to define a ratio between the results of two ComplexityCalculators.

    Attributes:
        name: The name for this ratio metric (e.g., "Words Per Sentence").
        numerator: The name of the ComplexityCalculator providing the numerator.
        denominator: The name of the ComplexityCalculator providing the denominator.
        percentage: If True, the result will be expressed as a percentage.
    """

    name: str
    numerator: str
    denominator: str
    percentage: bool = False

    def as_percentage(self) -> 'ComplexityRatio':
        """Returns a new ComplexityRatio instance configured to output as a percentage."""
        return ComplexityRatio(self.name, self.numerator, self.denominator, True)


# All our calculators and results are referenced by a name e.g. "Grammar Depth"
ComplexityResults = OrderedDict[str, Any]


class ComplexityCalculators:
    """
    Manages and applies a collection of ComplexityCalculator instances and
    ComplexityRatio definitions to spaCy Doc objects.

    This class orchestrates the calculation of multiple metrics over one or
    more documents. It processes documents sentence by sentence and token by
    token, aggregates results from individual calculators, and then computes
    any defined ratios.

    Results are stored in an OrderedDict, preserving the order in which the metrics 
    are added to the collection.
    """

    def __init__(self) -> None:
        self.calculators: OrderedDict[str, ComplexityCalculator] = OrderedDict()
        self.ratios: OrderedDict[str, ComplexityRatio] = OrderedDict()

    def add(self, name: str, c: ComplexityCalculator):
        """Adds a ComplexityCalculator instance to the collection.

        Args:
            name: The name to register this calculator under.
            c: The ComplexityCalculator instance.
        """
        self.calculators[name] = c

    def addRatio(self, ratio: ComplexityRatio):
        """Adds a ComplexityRatio definition to the collection.

        Args:
            ratio: The ComplexityRatio object to add.
        """
        self.ratios[ratio.name] = ratio

    def __getitem__(self, key: str) -> Any:
        """Allows accessing calculators or ratios by name."""
        if key in self.calculators:
            return self.calculators[key]
        elif key in self.ratios:
            return self.ratios[key]
        else:
            raise KeyError(f"No calculator or ratio: {key}")

    @profile
    def __get_token_values(self, token: Token) -> ComplexityResults:
        """Applies all registered token processors to a single token."""
        return ComplexityResults(
            [(name, c.process_token(token)) for name, c in self.calculators.items()]
        )

    @profile
    def __get_sentence_values(self, sent: Span) -> ComplexityResults:
        """Applies all sentence processors to a sentence and aggregates token processor results for its tokens."""
        sentence_results = ComplexityResults(
            [(name, c.process_sentence(sent)) for name, c in self.calculators.items()]
        )

        token_results = reduce(
            self.__merge, (self.__get_token_values(token_item) for token_item in sent)
        )
        return self.__merge(sentence_results, token_results)

    @profile
    def __get_values(self, doc: Doc) -> ComplexityResults:
        """Applies all calculators to a single spaCy Doc and returns aggregated results."""
        return reduce(
            self.__merge,
            (self.__get_sentence_values(sent_item) for sent_item in doc.sents),
            self.__get_initial_values(),
        )

    def __get_initial_values(self) -> ComplexityResults:
        """Returns a dictionary of null results, one for each registered calculator."""
        return OrderedDict(
            (name, c.null_value()) for name, c in self.calculators.items()
        )

    @profile
    def __merge(self, x: ComplexityResults, y: ComplexityResults) -> ComplexityResults:
        """Merges two ComplexityResults objects using each calculator's combine_values method.
        This is the "reduce" part of map/reduce."""
        return ComplexityResults(
            [
                (
                    name,
                    c.combine_values(x[name], y[name]),
                )
                for name, c, in self.calculators.items()
            ]
        )

    def __get_ratio(self, ratio: ComplexityRatio, calculationResults: ComplexityResults) -> Any:
        """Calculates a single ratio from the provided calculation results."""
        numerator = calculationResults[ratio.numerator]
        denominator = calculationResults[ratio.denominator]
        result = numerator / denominator if denominator > 0 else 0
        return int(result * 100) if ratio.percentage else round(result, 1)

    def __get_ratios(self, calculationResults: ComplexityResults) -> list[list[Any]]:
        """Calculates all defined ratios based on the provided calculation results."""
        return [
            [name, self.__get_ratio(ratio, calculationResults)]
            for name, ratio in self.ratios.items()
        ]

    @profile
    def get_results(self, docs: Iterable[Doc]) -> ComplexityResults:
        """Applies all calculators and ratios to an iterable of spaCy Docs and returns the final results.

        Args:
            docs: An iterable of spaCy Doc objects to process.

        Returns:
            An OrderedDict containing all calculated metrics and ratios.
        """
        results = reduce(
            lambda a, b: self.__merge(a, b),
            (self.__get_values(doc_item) for doc_item in docs),
            self.__get_initial_values(),
        )
        results = self.__and_finally(results)

        for k, v in self.__get_ratios(results):
            results[k] = v

        return results

    def __and_finally(self, results: ComplexityResults) -> ComplexityResults:
        """Applies the 'and_finally' method of each calculator to its respective result."""
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
def __grammar_depth(root_token: Token) -> int:
    """Recursively calculates the depth of the grammatical dependency tree from a root token.

    Args:
        root_token: The root token of the current subtree.

    Returns:
        The depth of the subtree rooted at root_token.
    """
    return 1 + max((__grammar_depth(child) for child in root_token.children), default=0)


@profile
def sentence_grammar_depth(sent: Span) -> int:
    """Calculates the maximum grammatical dependency depth of a sentence.

    Identifies the ROOT token(s) of the sentence and computes the depth
    of the dependency tree starting from the (first) ROOT.
    Assumes a single ROOT per sentence for typical well-formed sentences.

    Args:
        sent: The spaCy Span representing the sentence.

    Returns:
        The maximum grammar depth of the sentence.

    Raises:
        AssertionError: If no ROOT token or more than one ROOT token is found.
    """
    roots = [token for token in sent if token.dep_ == "ROOT"]
    assert len(roots) == 1, f"Sentence should have exactly one ROOT. Found {len(roots)} in: '{sent.text}'"
    return __grammar_depth(roots[0])


def words_known(token: Token, vocabulary: set[str]) -> int:
    """Checks if a token is considered 'known' based on a vocabulary set.

    A token is known if its text is in the vocabulary or if it's a digit.
    The match is not lemma-based.

    Args:
        token: The spaCy Token to check.
        vocabulary: A set of known word strings.

    Returns:
        1 if the token is known, 0 otherwise.
    """
    return 1 if ((token.text in vocabulary) or token.is_digit) else 0
