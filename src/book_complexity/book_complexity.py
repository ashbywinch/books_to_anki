"""Calculate various complexity metrics for texts in human language"""

import glob
from typing import OrderedDict, TextIO, cast

# from line_profiler import profile

from book_complexity.ComplexityCalculators import (
    ComplexityCalculator,
    ComplexityCalculators,
    ComplexityRatio,
    sentence_grammar_depth,
    word_length,
    sentence_count,
    vocabulary_level,
    word_count,
    words_known,
)
import spacy
import click
import alive_progress

import unicodecsv

from tabulate import tabulate


def make_nlp(pipeline: str):
    """Create a Spacy pipeline set up for complexity analysis"""
    return spacy.load(pipeline, exclude=["lemmatizer", "ner", "attribute_ruler"])


def build_calculators(
    vocabulary: set[str] | None,
    frequency: dict[str, int] | None,
    levels: list[range] | None,
) -> OrderedDict[str, ComplexityCalculator]:
    """Assemble the list of complexity calculators that we'll use in this run"""
    calculators = OrderedDict(
        [
            (
                "Sentence Count",
                ComplexityCalculator(process_sentence=sentence_count),
            ),
            ("Word Count", ComplexityCalculator(process_token=word_count)),
            (
                "Cumulative Word Length",
                ComplexityCalculator(process_token=word_length),
            ),
            (
                "Cumulative Grammar Depth",
                ComplexityCalculator(process_sentence=sentence_grammar_depth),
            ),
        ]
    )
    if vocabulary:
        calculators["Words Known"] = ComplexityCalculator(
            process_token=lambda token: words_known(token, cast(set[str], vocabulary))
        )

    if frequency and levels:
        calculators["Vocabulary Level"] = ComplexityCalculator(
            process_token=lambda token: vocabulary_level(
                token, cast(dict[str, int], frequency), cast(list[range], levels)
            ),
            combine_values=max,
        )
    return calculators


def build_ratios(vocabulary: set[str] | None) -> OrderedDict[str, ComplexityRatio]:
    """Assemble the list of ratio calculators that we'll use in this run"""
    ratios = OrderedDict(
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
        ratios["Percent Words Known"] = ComplexityRatio(
            "Words Known",
            "Word Count",
            percentage=True,
        )
    return ratios


# @profile
def generate_docs(nlp, inputfile):
    for line in inputfile:
        docs = nlp.pipe([line.strip()])
        for doc in docs:
            yield doc


# @profile
def get_book_complexity(
    inputfile,
    nlp,
    vocabulary: set[str] | None = None,
    frequency: dict[str, int] | None = None,
    levels: list[range] | None = None,
) -> dict[str, int]:
    """Calculate and return the complexity of a single file
    (or other iterable that produces strings)"""
    calculators = ComplexityCalculators(
        build_calculators(vocabulary, frequency, levels), build_ratios(vocabulary)
    )
    docs = generate_docs(nlp, inputfile)
    results = calculators.get_results(docs)
    for k in [k for k in results.keys() if k.startswith("Cumulative")]:
        results.pop(k)  # these were just to calculate the ratios, let's lose them
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

    complexity = get_book_complexity(
        inputfile, nlp, known_morph_list, frequency_list, levels
    )

    print(tabulate([[k, v] for k, v in complexity.items()]))


def morphs_from_csv(knownmorphs) -> set[str]:
    known_morph_list = set()
    morph_reader = unicodecsv.reader(knownmorphs)
    for row in morph_reader:
        known_morph_list.add(row[1])
    return known_morph_list


def frequencies_from_csv(frequencycsv) -> dict[str, int]:
    frequency_reader = unicodecsv.reader(frequencycsv)
    frequencies: dict[str, int] = {}
    for index, words in enumerate(frequency_reader):
        (lemma, inflection) = words
        if index > 1:  # skip the header row
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


def get_books_complexity(
    inputfolder: str,
    pipeline: str,
    knownmorphs: TextIO,
    frequencycsv: TextIO,
    outputcsv: TextIO,
):
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
                    complexity = get_book_complexity(
                        file, nlp, known_morph_list, frequencies, levels
                    )
                    if index == 0:
                        writer.writerow(["Filename"] + list(complexity.keys()))
                    writer.writerow([file.name] + list(complexity.values()))
                bar.text(filename)
                bar()


@click.command()
@click.argument("inputfolder", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb"),
    help="Known Morphs csv from Ankimorphs",
)
@click.option(
    "--frequencycsv",
    type=click.File(mode="rb"),
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
    get_books_complexity(inputfolder, pipeline, knownmorphs, frequencycsv, outputcsv)
