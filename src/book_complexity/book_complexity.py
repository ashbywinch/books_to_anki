"""Calculate various complexity metrics for texts in human language"""

import glob
from pathlib import Path
from line_profiler import profile
from typing import Any, Optional, OrderedDict, TextIO, cast
import orjsonl as jsonl
from spacy.tokens import Token, Span


# from line_profiler import profile

from book_complexity.ComplexityCalculators import (
    ComplexityCalculator,
    ComplexityCalculators,
    ComplexityRatio,
    sentence_grammar_depth,
    words_known,
)
import spacy
import click
import alive_progress  # type: ignore

import unicodecsv  # type: ignore

from tabulate import tabulate

from book_complexity.vocabulary_levels import VocabLevelCalculator, VocabLevels
from book_to_flashcards import trim_title


def make_nlp(pipeline: str):
    """Create a Spacy pipeline set up for complexity analysis"""
    return spacy.load(pipeline, exclude=["lemmatizer", "ner", "attribute_ruler"])


class WordCountCalculator(ComplexityCalculator):
    name = "Word Count"

    def process_token(self, token: Token) -> int:
        return 0 if token.is_punct or token.is_digit or token.is_space else 1


class SentenceCountCalculator(ComplexityCalculator):
    name = "Sentence Count"

    def process_sentence(self, sentence: Span) -> int:
        return 1


class CumulativeWordLengthCalculator(ComplexityCalculator):
    name = "Cumulative Word Length"

    def process_token(self, token: Token):
        return (
            0 if token.is_punct or token.is_digit or token.is_space else len(token.text)
        )


class GrammarDepthCalculator(ComplexityCalculator):
    name = "Cumulative Grammar Depth"

    def process_sentence(self, sentence: Span):
        return sentence_grammar_depth(sentence)


class WordsKnownCalculator(ComplexityCalculator):
    name = "Words Known"

    def __init__(self, vocabulary):
        self.vocabulary = vocabulary

    def process_token(self, token: Token):
        return words_known(token, cast(set[str], self.vocabulary))


@profile
def generate_docs(nlp, inputfile):
    for line in inputfile:
        docs = nlp.pipe([line.strip()])
        for doc in docs:
            yield doc


@profile
def get_book_complexity(
    inputfile,
    nlp,
    vocab_levels:Optional[VocabLevels] = None,
    vocabulary: Optional[set[str]] = None,
) -> OrderedDict[str, Any]:
    """Calculate and return the complexity of a single file
    (or other iterable that produces strings)"""
    calculators = ComplexityCalculators()
    calculators.add("Word Count", WordCountCalculator())
    calculators.add("Sentence Count", SentenceCountCalculator())
    calculators.add("Cumulative Grammar Depth", GrammarDepthCalculator())
    calculators.add("Cumulative Word Length", CumulativeWordLengthCalculator())

    if vocabulary:
        calculators.add("Words Known", WordsKnownCalculator(vocabulary))
    if vocab_levels:
        calculators.add("Vocab Level", VocabLevelCalculator(vocab_levels, small_sample_size_cutoff=10))

    calculators.addRatio(
        ComplexityRatio("Mean Words Per Sentence", "Word Count", "Sentence Count")
    )
    calculators.addRatio(
        ComplexityRatio("Mean Word Length", "Cumulative Word Length", "Word Count")
    )
    calculators.addRatio(
        ComplexityRatio(
            "Mean Grammar Depth", "Cumulative Grammar Depth", "Sentence Count"
        )
    )
    if vocabulary:
        calculators.addRatio(
            ComplexityRatio(
                "Percent Words Known", "Words Known", "Word Count"
            ).as_percentage()
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


def get_book_props(filename: str, separator = None):
    title = trim_title(Path(filename).stem, separator)
    author = Path(filename).parent.stem
    return {"title": title, "author": author}

def get_complexities(files, nlp, known_morph_list, vocab:VocabLevels):
    for filename in files:
        with open(filename, "r", encoding="utf-8") as file:
            complexity = get_book_complexity(file, nlp, known_morph_list, vocab)
            yield {"lang": nlp.meta["lang"]} | get_book_props(file.name) | complexity

levels = {
    "A1": range(0, 1000),
    "A2": range(1000, 2000),
    "B1": range(2000, 5000),
    "B2": range(5000, 10000),
    "C1": range(10000, 20000),
    "C2": range(20000, 99999999),
}
def get_books_complexity(
    inputfolder: str,
    pipeline: str,
    knownmorphs: TextIO,
    frequencycsv: TextIO,
    outputfilename: str,
):
    """Calculate the complexity of all text files in a folder, and
    output a jsonl file with one line per text file"""
    if Path(outputfilename).exists():
        raise Exception(f"File {outputfilename} already exists")
    
    files = glob.glob(inputfolder + "/**/*.txt", recursive=True)
    with alive_progress.alive_bar(len(files), bar="bubbles", spinner="classic") as bar:
        nlp = make_nlp(pipeline)
        known_morph_list = morphs_from_csv(knownmorphs) if knownmorphs else None
        frequencies = frequencies_from_csv(frequencycsv) if frequencycsv else None
        data = get_complexities(
            files=files,
            nlp=nlp,
            known_morph_list=known_morph_list,
            vocab=VocabLevels(frequencies, levels)
        )
        for row in data:
            jsonl.append(outputfilename, row)
            bar()
