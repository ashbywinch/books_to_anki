"""Calculate various complexity metrics for texts in human language"""

from dataclasses import dataclass
from functools import reduce
import glob
from typing import OrderedDict

from book_complexity.ComplexityCalculators import (
    ComplexityCalculator,
    cumulative_grammar_depth,
    cumulative_word_length,
    sentence_count,
    vocabulary_level,
    word_count,
    words_known,
)
import spacy
from spacy.tokens import Doc
import click
import alive_progress

import unicodecsv

from tabulate import tabulate


def make_nlp(pipeline: str):
    """Create a Spacy pipeline set up for complexity analysis"""
    return spacy.load(pipeline, exclude=["lemmatizer", "ner", "attribute_ruler"])


@dataclass
class ComplexityRatio:
    numerator: str
    denominator: str
    percentage: bool = False


class ComplexityCalculators:

    def __init__(
        self,
        vocabulary: set[str] = None,
        frequency: dict[str, int] = None,
        levels: list[range] = None,
    ):
        self.calculators = OrderedDict(
            [
                ("Sentence Count", ComplexityCalculator(sentence_count)),
                ("Word Count", ComplexityCalculator(word_count)),
                (
                    "Cumulative Word Length",
                    ComplexityCalculator(cumulative_word_length),
                ),
                (
                    "Cumulative Grammar Depth",
                    ComplexityCalculator(cumulative_grammar_depth),
                ),
            ]
        )
        if vocabulary:
            self.calculators["Words Known"] = ComplexityCalculator(
                lambda doc: words_known(doc, vocabulary)
            )

        if frequency and levels:
            self.calculators["Vocabulary Level"] = ComplexityCalculator(
                lambda doc: vocabulary_level(doc, frequency, levels),
                max,
            )

        self.ratios = OrderedDict(
            [
                (
                    "Mean Words Per Sentence",
                    ComplexityRatio(
                        "Word Count",
                        "Sentence Count",
                    ),
                ),
                (
                    "Mean Word Length",
                    ComplexityRatio(
                        "Cumulative Word Length",
                        "Word Count",
                    ),
                ),
                (
                    "Mean Grammar Depth",
                    ComplexityRatio(
                        "Cumulative Grammar Depth",
                        "Sentence Count",
                    ),
                ),
            ]
        )
        if vocabulary:
            self.ratios["Percent Words Known"] = ComplexityRatio(
                "Words Known",
                "Word Count",
                percentage=True,
            )

    def calculate_ratio(
        self, ratio: ComplexityRatio, results: OrderedDict[str, int]
    ) -> int:
        numerator = results[ratio.numerator]
        denominator = results[ratio.denominator]
        result = numerator / denominator if denominator > 0 else 0
        return int(result * 100) if ratio.percentage else round(result, 1)

    def get_values(self, doc: Doc) -> OrderedDict[str, int]:
        return OrderedDict(
            [name, c.get_value(doc)] for name, c in self.calculators.items()
        )

    def reduce(
        self, x: OrderedDict[str, int], y: OrderedDict[str, int]
    ) -> OrderedDict[str, int]:
        """Call the combine_values function from each calculator on the corresponding values in these two lists
        resulting in a single list with an accumulated result for each calculator"""
        return OrderedDict(
            [
                [name, c.combine_values(x, y)]
                for name, c, x, y in zip(
                    self.calculators.keys(),
                    self.calculators.values(),
                    x.values(),
                    y.values(),
                )
            ]
        )

    def get_ratios(self, results: OrderedDict[str, int]):
        return [
            [name, self.calculate_ratio(ratio, results)]
            for name, ratio in self.ratios.items()
        ]


def generate_docs(nlp, inputfile):
    for line in inputfile:
        docs = nlp.pipe([line.strip()])
        for doc in docs:
            yield doc


def book_complexity(
    inputfile,
    nlp,
    vocabulary: set[str] = None,
    frequency: dict[str, int] = None,
    levels: list[range] = None,
) -> dict[str, int]:
    """Calculate and return the complexity of a single file
    (or other iterable that produces strings)"""
    calculators = ComplexityCalculators(vocabulary, frequency, levels)
    docs = generate_docs(nlp, inputfile)
    results = reduce(
        lambda a, b: calculators.reduce(a, b),
        map(lambda doc: calculators.get_values(doc), docs),
    )
    for k, v in calculators.get_ratios(results):
        results[k] = v
    for k in [k for k in results.keys() if k.startswith("Cumulative")]:
        results.pop(k)  # these were only useful to calculate the ratios!
    return results


@click.command()
@click.argument("inputfile", type=click.File(mode="r", encoding="utf-8"))
@click.option(
    "--pipeline", help="Name of spacy pipeline to read file"
)  # ru_core_news_sm
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb", encoding="utf-8"),
    help="Known Morphs csv from Ankimorphs",
)
@click.option(
    "--frequencycsv",
    type=click.File(mode="rb", encoding="utf-8"),
    help="Word frequency list for the language the file is in",
)
def cli_book_complexity(inputfile, pipeline, knownmorphs, frequencycsv):
    """Calculate complexity of a single text file and send it to the console"""
    nlp = make_nlp(pipeline)

    known_morph_list = morphs_from_csv(knownmorphs) if knownmorphs else None
    frequency_list = frequencies_from_csv(frequencycsv) if frequencycsv else None

    complexity = book_complexity(
        inputfile, nlp, known_morph_list, frequency_list, levels
    )

    print(tabulate([[k, v] for k, v in complexity.items()]))


def morphs_from_csv(knownmorphs):
    known_morph_list = set()
    morph_reader = unicodecsv.reader(knownmorphs)
    for row in morph_reader:
        known_morph_list.add(row[1])
    return known_morph_list


def frequencies_from_csv(frequencies):
    frequency_reader = unicodecsv.reader(frequencies)
    frequencies: dict[int, str] = {}
    for index, words in enumerate(frequency_reader):
        (lemma, inflection) = words
        if index > 1:  # there's a header row
            frequencies[inflection] = index
    return frequencies


levels = [
    range(0, 600),
    range(600, 1200),
    range(1200, 2500),
    range(2500, 5000),
    range(5000, 10000),
    range(20000, 99999999),
]


@click.command()
@click.argument("inputfolder", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb", encoding="utf-8"),
    help="Known Morphs csv from Ankimorphs",
)
@click.option(
    "--frequencycsv",
    type=click.File(mode="rb", encoding="utf-8"),
    help="Frequency file for the language used",
)
@click.option(
    "--pipeline", help="Name of spacy pipeline to read files"
)  # ru_core_news_sm
@click.option(
    "--outputcsv",
    type=click.File(mode="wb"),
    help="Name of a csv file to put the results",
)
def cli_books_complexity(inputfolder, pipeline, knownmorphs, frequencycsv, outputcsv):
    """Calculate the complexity of all text files in a folder, and
    output a CSV with one line per text file"""
    nlp = make_nlp(pipeline)
    known_morph_list = morphs_from_csv(knownmorphs) if knownmorphs else None
    frequencies = frequencies_from_csv(frequencycsv) if frequencycsv else None

    files = glob.glob(inputfolder + "/**/*.txt", recursive=True)
    if outputcsv:
        with alive_progress.alive_bar(
            len(files), bar="bubbles", spinner="classic"
        ) as bar:
            writer = unicodecsv.writer(outputcsv)

            for index, filename in enumerate(files):
                with open(filename, "r", encoding="utf-8") as file:
                    complexity = book_complexity(
                        file, nlp, known_morph_list, frequencies, levels
                    )
                    if index == 0:
                        writer.writerow(["Filename"] + list(complexity.keys()))
                    writer.writerow([file.name] + list(complexity.values()))
                bar.text(filename)
                bar()
