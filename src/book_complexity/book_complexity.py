"""Calculate various complexity metrics for texts in human language"""

import glob

from book_complexity.ComplexityCalculators import (
    ComplexityRatio,
    CumulativeGrammarDepthComplexityCalculator,
    CumulativeWordLengthComplexityCalculator,
    SentenceCountComplexityCalculator,
    VocabularyLevelComplexityCalculator,
    WordCountComplexityCalculator,
    WordsKnownComplexityCalculator,
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


class ComplexityCalculators:

    def __init__(
        self,
        vocabulary: set[str] = None,
        frequency: dict[str, int] = None,
        levels: list[range] = None,
    ):
        self.sentence_counter = SentenceCountComplexityCalculator()
        self.word_counter = WordCountComplexityCalculator()
        self.cumulative_word_length_counter = CumulativeWordLengthComplexityCalculator()
        self.cumulative_grammar_depth_counter = (
            CumulativeGrammarDepthComplexityCalculator()
        )
        self.calculators = [
            self.sentence_counter,
            self.word_counter,
            self.cumulative_word_length_counter,
            self.cumulative_grammar_depth_counter,
        ]
        if vocabulary:
            self.words_known_calculator = WordsKnownComplexityCalculator(vocabulary)
            self.calculators.append(self.words_known_calculator)

        if frequency and levels:
            self.calculators.append(
                VocabularyLevelComplexityCalculator(frequency, levels)
            ),

        self.ratios = [
            ComplexityRatio(
                "Mean Words Per Sentence",
                self.word_counter,
                self.sentence_counter,
            ),
            ComplexityRatio(
                "Mean word length",
                self.cumulative_word_length_counter,
                self.word_counter,
            ),
            ComplexityRatio(
                "Mean grammar depth",
                self.cumulative_grammar_depth_counter,
                self.sentence_counter,
            ),
        ]
        if vocabulary:
            self.ratios.append(
                ComplexityRatio(
                    "Percent Words Known",
                    self.words_known_calculator,
                    self.word_counter,
                    percentage=True,
                )
            )

    def read(self, doc: Doc):
        for c in self.calculators:
            c.read(doc)

    def values(self):
        return {c.name: c.value() for c in self.calculators} | {
            c.name: c.value() for c in self.ratios
        }


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

    for line in inputfile:
        docs = nlp.pipe([line.strip()])
        for doc in docs:
            calculators.read(doc)

    return calculators.values()


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

            headers = book_complexity("", nlp, known_morph_list, frequencies, levels)
            writer.writerow(["Filename"] + list(headers.keys()))
            for filename in files:
                with open(filename, "r", encoding="utf-8") as file:
                    complexity = book_complexity(
                        file, nlp, known_morph_list, frequencies, levels
                    )
                    writer.writerow([file.name] + list(complexity.values()))
                bar.text(filename)
                bar()
