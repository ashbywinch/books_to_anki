"""
Calculates various complexity metrics for texts in human language.

This module provides:
- A collection of `ComplexityCalculator` classes for individual metrics
  (e.g., Word Count, Sentence Count, Grammar Depth).
- The `get_book_complexity` function to analyze a single text file or iterable
  of strings and return a dictionary of calculated complexity scores.
- The `get_books_complexity` function, which processes all .txt files in a specified
  folder and outputs results to a JSONL file. This function serves as an engine
  for batch processing but is not directly exposed as a command-line interface
  in this script.
- A command-line interface (`cli_book_complexity`) via Click for analyzing
  a single text file and printing its complexity results to the console.
- Vocabulary level estimation based on word frequencies, using a `levels` dictionary
  (mapping CEFR-like levels to word count thresholds) via the `VocabLevelCalculator`.
"""

import glob
from pathlib import Path
from line_profiler import profile # type: ignore
from typing import Any, Optional, OrderedDict, TextIO, cast, Generator, Union, BinaryIO
import orjsonl as jsonl
import spacy # type: ignore
from spacy.tokens import Token, Span # type: ignore
from spacy.language import Language # type: ignore


# from line_profiler import profile

from book_complexity.ComplexityCalculators import (
    ComplexityCalculator,
    ComplexityCalculators,
    ComplexityRatio,
    sentence_grammar_depth,
    words_known,
)
# import spacy 
import click
import alive_progress  # type: ignore

import unicodecsv  # type: ignore

from tabulate import tabulate

from book_complexity.vocabulary_levels import VocabLevelCalculator, VocabLevels
from book_to_flashcards import trim_title 

# Word count threshold below which vocabulary level metrics are not calculated.
# This is to avoid potentially misleading results from insufficient text data.
DEFAULT_SMALL_SAMPLE_SIZE_CUTOFF = 250


def make_nlp(pipeline: str) -> Language:
    """Create a spaCy pipeline optimized for complexity analysis.

    Excludes 'lemmatizer', 'ner', and 'attribute_ruler' as they are not
    required for the current set of complexity metrics, improving loading
    time and memory usage.

    Args:
        pipeline: The name of the spaCy pipeline to load (e.g., 'en_core_web_sm').

    Returns:
        A loaded spaCy nlp object.
    """
    return spacy.load(pipeline, exclude=["lemmatizer", "ner", "attribute_ruler"])


class WordCountCalculator(ComplexityCalculator):
    """Calculates the total number of words, excluding punctuation, digits, and spaces."""
    name = "Word Count"

    def process_token(self, token: Token) -> int:
        return 0 if token.is_punct or token.is_digit or token.is_space else 1


class SentenceCountCalculator(ComplexityCalculator):
    """Calculates the total number of sentences."""
    name = "Sentence Count"

    def process_sentence(self, sentence: Span) -> int:
        return 1


class CumulativeWordLengthCalculator(ComplexityCalculator):
    """Calculates the sum of the lengths of all words, excluding punctuation, digits, and spaces."""
    name = "Cumulative Word Length"

    def process_token(self, token: Token):
        return (
            0 if token.is_punct or token.is_digit or token.is_space else len(token.text)
        )


class GrammarDepthCalculator(ComplexityCalculator):
    """Calculates the sum of the grammatical depth of each sentence."""
    name = "Cumulative Grammar Depth"

    def process_sentence(self, sentence: Span):
        return sentence_grammar_depth(sentence)


class WordsKnownCalculator(ComplexityCalculator):
    """Calculates the number of words in the input that are present in a provided vocabulary set."""
    name = "Words Known"

    def __init__(self, vocabulary: set[str]):
        """
        Args:
            vocabulary: A set of known word strings.
        """
        self.vocabulary = vocabulary

    def process_token(self, token: Token):
        return words_known(token, cast(set[str], self.vocabulary))


@profile
def generate_docs(nlp: Language, inputfile: TextIO) -> Generator[spacy.tokens.Doc, Any, Any]:
    """Processes lines from an input file and yields spaCy Doc objects.

    Args:
        nlp: The spaCy nlp object.
        inputfile: A text file object (or any iterable yielding strings).

    Yields:
        spaCy Doc objects, one for each processed line.
    """
    for line in inputfile:
        docs = nlp.pipe([line.strip()])
        for doc in docs:
            yield doc


@profile
def get_book_complexity(
    inputfile: TextIO,
    nlp: Language,
    vocab_levels:Optional[VocabLevels] = None,
    vocabulary: Optional[set[str]] = None,
    small_sample_size_cutoff: int = DEFAULT_SMALL_SAMPLE_SIZE_CUTOFF,
) -> OrderedDict[str, Any]:
    """Calculate and return a dictionary of complexity metrics for a single text.

    Args:
        inputfile: A file object or other iterable that yields strings (lines of text).
        nlp: The spaCy nlp object for processing the text.
        vocab_levels: An optional VocabLevels object for configuring vocabulary level metrics.
        vocabulary: An optional set of known words for calculating "Words Known" metrics.
        small_sample_size_cutoff: Word count below which vocabulary level is not calculated.

    Returns:
        An OrderedDict containing metric names as keys and their calculated values.
        Intermediate "Cumulative" metrics used for ratios are removed from the final output.
    """
    calculators = ComplexityCalculators()
    calculators.add("Word Count", WordCountCalculator())
    calculators.add("Sentence Count", SentenceCountCalculator())
    calculators.add("Cumulative Grammar Depth", GrammarDepthCalculator())
    calculators.add("Cumulative Word Length", CumulativeWordLengthCalculator())

    if vocabulary:
        calculators.add("Words Known", WordsKnownCalculator(vocabulary))
    if vocab_levels:
        calculators.add("Vocab Level", VocabLevelCalculator(vocab_levels, small_sample_size_cutoff=small_sample_size_cutoff))

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
    for k in [key for key in results.keys() if key.startswith("Cumulative")]:
        results.pop(k)  # these were just to calculate the ratios, let's lose them
    return results


@click.command()
@click.argument("inputfile", type=click.File(mode="r", encoding="utf-8"))
@click.option(
    "--pipeline", required=True, help="Name of spaCy pipeline to use (e.g., 'en_core_web_sm')."
)
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb"), # unicodecsv expects byte stream
    help="Path to a CSV file of known morphs (e.g., from AnkiMorphs). Expected format: one morph per line in the second column.",
)
@click.option(
    "--frequencycsv",
    type=click.File(mode="rb"), # unicodecsv often expects byte stream
    help="Path to a CSV file containing word frequencies for the text's language. Expected format: lemma,inflection per line, with frequency implied by order.",
)
def cli_book_complexity(inputfile: TextIO, pipeline: str, knownmorphs: Optional[BinaryIO], frequencycsv: Optional[BinaryIO]):
    """Calculates and prints complexity metrics for a single text file.

    The results are printed to the console in a table format.
    """
    nlp = make_nlp(pipeline)

    known_morph_list = morphs_from_csv(knownmorphs) if knownmorphs else None
    vocab_levels_obj = None
    if frequencycsv:
        frequency_list = frequencies_from_csv(frequencycsv)
        # 'levels' is the global 'levels' dictionary defined in this file
        vocab_levels_obj = VocabLevels(frequencies=frequency_list, levels=levels)

    complexity = get_book_complexity(
        inputfile, nlp, vocab_levels=vocab_levels_obj, vocabulary=known_morph_list
    )

    print(tabulate([[k, v] for k, v in complexity.items()]))


def morphs_from_csv(knownmorphs_file: BinaryIO) -> set[str]:
    """Reads known morphs from a CSV file.

    Expects a CSV file where the second column of each row contains a morph.
    The CSV is read with UTF-8 encoding.

    Args:
        knownmorphs_file: A binary file object for the CSV containing known morphs.

    Returns:
        A set of known morph strings.
    """
    known_morph_list = set()
    morph_reader = unicodecsv.reader(knownmorphs_file, encoding='utf-8')
    for row in morph_reader:
        if len(row) > 1: # Ensure row has at least two columns
            known_morph_list.add(row[1])
    return known_morph_list


def frequencies_from_csv(frequencycsv_file: BinaryIO) -> dict[str, int]:
    """Reads word frequencies from a CSV file.

    Expects a CSV file where each row after the header contains 'lemma,inflection'.
    The line number (minus 1 for the header) is used as the frequency rank.
    The CSV is read with UTF-8 encoding.

    Args:
        frequencycsv_file: A binary file object for the CSV containing word frequencies.

    Returns:
        A dictionary mapping 'lemma,inflection' strings to their integer frequency rank 
        (lower is more frequent).
    """
    frequency_list: dict[str, int] = {}
    freq_reader = unicodecsv.reader(frequencycsv_file, encoding='utf-8')
    next(freq_reader)  # skip header
    for i, row in enumerate(freq_reader):
        if len(row) != 2:
            raise ValueError(
                f"Malformed row in frequency CSV at data line {i+1} (actual line {i+2}): "
                f"Expected 2 columns (lemma, inflection), got {len(row)}. Row content: {row}"
            )
        # If row is valid, proceed
        _lemma, inflection = row[0], row[1]
        frequency_list[inflection] = i 
    return frequency_list


def get_book_props(filename: str, remove_title_suffix_after: Optional[str] = None) -> dict[str, str]:
    """Extracts book title and author from a filename and its containing directory path.

    The function assumes the book's title can be derived from the filename's stem
    (the filename without its final suffix/extension). This stem can optionally be
    further trimmed using the `remove_title_suffix_after` string.
    The author is assumed to be the name of the parent directory containing the file.

    Args:
        filename: The full path to the book file (e.g., "/path/to/Author Name/Book Title_extra.txt").
        remove_title_suffix_after: Optional string. If provided, the filename stem
                                   (e.g., "Book Title_extra") is passed to `trim_title`
                                   along with this string to remove the suffix.
                                   For example, if `_extra` is passed, the title becomes "Book Title".

    Returns:
        A dictionary with 'title' and 'author' keys.
        Example: {"title": "Book Title", "author": "Author Name"}
    """
    title = trim_title(Path(filename).stem, remove_title_suffix_after)
    author = Path(filename).parent.stem
    return {"title": title, "author": author}

def get_complexities(
    files: list[str],
    nlp: Language,
    known_morph_list: Optional[set[str]],
    vocab: Optional[VocabLevels], # Made Optional to handle case where frequencycsv is not provided
    small_sample_size_cutoff: int,
    remove_title_suffix_after: Optional[str] = None
) -> Generator[dict[str, Any], Any, Any]:
    """Generates complexity data for a list of text files.

    This function iterates through a list of provided file paths. For each file,
    it opens the file, calculates its complexity metrics using `get_book_complexity`,
    and extracts metadata (language from the nlp object, title and author using
    `get_book_props`). It then yields a single dictionary combining all this
    information for the processed file.

    Args:
        files: A list of file paths to process.
        nlp: The spaCy `Language` object used for text processing.
        known_morph_list: An optional set of known morphs, passed to `get_book_complexity`.
        vocab: An optional `VocabLevels` object for vocabulary level calculations,
               passed to `get_book_complexity`.
        small_sample_size_cutoff: Word count threshold below which vocabulary level
                                  metrics are not calculated, passed to `get_book_complexity`.
        remove_title_suffix_after: Optional string used by `get_book_props` to trim
                                   titles derived from filenames.

    Yields:
        A dictionary for each processed file. The dictionary contains keys such as
        'lang', 'title', 'author', and various complexity metric keys returned by
        `get_book_complexity` (e.g., 'Word Count', 'Mean Words Per Sentence',
        'Vocab Level').
    """
    for filename in files:
        with open(filename, "r", encoding="utf-8") as file:
            complexity = get_book_complexity(file, nlp, vocab_levels=vocab, vocabulary=known_morph_list, small_sample_size_cutoff=small_sample_size_cutoff)
            yield {"lang": nlp.meta["lang"]} | get_book_props(file.name, remove_title_suffix_after=remove_title_suffix_after) | complexity

# Defines target vocabulary sizes for different CEFR-like proficiency levels.
# Used by VocabLevelCalculator to estimate the vocabulary level of a text.
# Keys are level names (e.g., "A1", "A2") and values identify ranges in a sorted
# word frequency list that a learner at that level might be expected to know.
levels = {
    "A1": range(0, 1000),
    "A2": range(1000, 2000),
    "B1": range(2000, 5000),
    "B2": range(5000, 10000),
    "C1": range(10000, 20000),
    "C2": range(20000, 99999999), # Using a large upper bound for C2
}

def get_books_complexity(
    inputfolder: str,
    pipeline: str,
    knownmorphs_file_arg: Optional[BinaryIO], # Renamed to avoid conflict with variable
    frequencycsv_file_arg: Optional[BinaryIO], # Renamed to avoid conflict with variable
    outputfilename: str,
    remove_title_suffix_after: Optional[str] = None,
    small_sample_size_cutoff: int = DEFAULT_SMALL_SAMPLE_SIZE_CUTOFF,
):
    """Calculates complexity for all .txt files in a folder and writes results to a JSONL file.

    This function drives the core logic for batch processing multiple books, used
    by the 'books-complexity' command-line tool. It displays a progress bar during processing.

    Args:
        inputfolder: Path to the folder containing .txt files (searched recursively).
        pipeline: Name of the spaCy pipeline to use.
        knownmorphs_file_arg: Optional binary file object for the known morphs CSV.
        frequencycsv_file_arg: Optional binary file object for the word frequency CSV.
        outputfilename: Path to the output JSONL file. The file must not already exist.
        remove_title_suffix_after: Optional string to trim from book titles derived from filenames.
        small_sample_size_cutoff: Word count cutoff for vocabulary level calculation.

    Raises:
        Exception: If the outputfilename already exists.
    """
    if Path(outputfilename).exists():
        raise Exception(f"File {outputfilename} already exists")
    files = glob.glob(inputfolder + "/**/*.txt", recursive=True)
    if not files:
        raise Exception(f"No .txt files found in {inputfolder}")

    with alive_progress.alive_bar(len(files), bar="bubbles", spinner="classic") as bar:
        nlp = make_nlp(pipeline)
        known_morph_list = morphs_from_csv(knownmorphs_file_arg) if knownmorphs_file_arg else None
        
        vocab_levels_instance: Optional[VocabLevels] = None
        if frequencycsv_file_arg:
            frequencies = frequencies_from_csv(frequencycsv_file_arg)
            vocab_levels_instance = VocabLevels(frequencies, levels)
            
        data = get_complexities(
            files=files,
            nlp=nlp,
            known_morph_list=known_morph_list,
            vocab=vocab_levels_instance,
            small_sample_size_cutoff=small_sample_size_cutoff,
            remove_title_suffix_after=remove_title_suffix_after
        )
        for row in data:
            jsonl.append(outputfilename, row)
            bar()
