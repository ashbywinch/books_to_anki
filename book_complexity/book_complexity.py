"""Calculate various complexity metrics for texts in human language"""

from dataclasses import dataclass
import glob
import spacy
import click
from spacy.tokens import Token

import unicodecsv

from tabulate import tabulate


def make_nlp(pipeline: str):
    """Create a Spacy pipeline set up for complexity analysis"""
    return spacy.load(pipeline, exclude=["lemmatizer", "ner", "attribute_ruler"])


@dataclass
class Complexity:
    """Various measures of document complexity, plus an overall complexity score"""

    word_count: int
    mean_grammar_depth: int
    mean_word_length: int
    mean_words_per_sentence: int
    overall_score: int


def grammar_depth(root_token: Token):
    """The depth of the grammatical tree, starting with root_token as the root of the tree"""

    # if there are no children, return 1, else return the maximum of the childrens' depths
    return 1 + max((grammar_depth(child) for child in root_token.children), default=0)


def book_complexity(inputfile, nlp) -> Complexity:
    """Calculate and return the complexity of a single file
    (or other iterable that produces strings)"""
    sents_count = 0
    word_count = 0
    cumulative_word_length = 0
    cumulative_grammar_depth = 0

    for line in inputfile:
        docs = nlp.pipe([line.strip()])
        for doc in docs:
            sents_count = sents_count + sum(1 for dummy in doc.sents)
            word_count = word_count + sum(
                1 for token in doc if not token.is_punct and not token.is_space
            )
            cumulative_word_length = cumulative_word_length + sum(
                len(token.text)
                for token in doc
                if not token.is_punct and not token.is_space
            )
            for sent in doc.sents:
                roots = [token for token in sent if token.dep_ == "ROOT"]
                assert len(roots) == 1
                cumulative_grammar_depth = cumulative_grammar_depth + grammar_depth(
                    roots[0]
                )

    complexity = Complexity(
        word_count=word_count,
        mean_words_per_sentence=int(word_count / sents_count) if sents_count > 0 else 0,
        mean_word_length=(
            int(cumulative_word_length / word_count) if word_count > 0 else 0
        ),
        mean_grammar_depth=(
            round(cumulative_grammar_depth / sents_count, 1) if sents_count > 0 else 0
        ),
        overall_score=0,
    )
    complexity.overall_score = (
        complexity.mean_words_per_sentence
        * complexity.mean_word_length
        * complexity.mean_grammar_depth
    )
    return complexity


@click.command()
@click.argument("inputfile", type=click.File(mode="r", encoding="utf-8"))
@click.option(
    "--pipeline", help="Name of spacy pipeline to read file"
)  # ru_core_news_sm
def cli_book_complexity(inputfile, pipeline):
    """Calculate complexity of a single text file and send it to the console"""
    nlp = make_nlp(pipeline)

    complexity = book_complexity(inputfile, nlp)
    print(f"Complexity of text file {inputfile.name}")

    print(
        tabulate(
            [
                ["Words", complexity.word_count],
                ["Mean word length", complexity.mean_word_length],
                ["Mean words per sentence", complexity.mean_words_per_sentence],
                ["Mean grammar depth", complexity.mean_grammar_depth],
                ["Complexity score", complexity.overall_score],
            ]
        )
    )


@click.command()
@click.argument("inputfolder", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--pipeline", help="Name of spacy pipeline to read files"
)  # ru_core_news_sm
@click.option(
    "--outputcsv",
    type=click.File(mode="wb"),
    help="Name of a csv file to put the results",
)
def cli_books_complexity(inputfolder, pipeline, outputcsv):
    """Calculate the complexity of all text files in a folder, and
    output a CSV with one line per text file"""
    nlp = make_nlp(pipeline)

    files = glob.glob(inputfolder + "/**/*.txt", recursive=True)
    if outputcsv:
        writer = unicodecsv.writer(outputcsv)
        writer.writerow(
            [
                "File name",
                "Word count",
                "Mean word length",
                "Mean words per sentence",
                "Mean grammar depth",
                "Overall Score",
            ]
        )

        for filename in files:
            with open(filename, "r", encoding="utf-8") as file:
                result = book_complexity(file, nlp)
                writer.writerow(
                    [
                        file.name,
                        result.word_count,
                        result.mean_word_length,
                        result.mean_words_per_sentence,
                        result.mean_grammar_depth,
                        result.overall_score,
                    ]
                )
