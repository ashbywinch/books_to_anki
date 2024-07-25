"""Calculate various complexity metrics for texts in human language"""

from dataclasses import dataclass
import glob
import spacy
import click
import alive_progress
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
    words_known: int
    percent_words_known: int
    overall_score: int


def grammar_depth(root_token: Token):
    """The depth of the grammatical tree, starting with root_token as the root of the tree"""

    # if there are no children, return 1, else return the maximum of the childrens' depths
    return 1 + max((grammar_depth(child) for child in root_token.children), default=0)


def book_complexity(inputfile, nlp, vocabulary: set[str] = None) -> Complexity:
    """Calculate and return the complexity of a single file
    (or other iterable that produces strings)"""
    sents_count = 0
    word_count = 0
    cumulative_word_length = 0
    cumulative_grammar_depth = 0
    words_you_know = 0

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
            if vocabulary:
                words_you_know = words_you_know + sum(
                    1 for token in doc if ((token.text in vocabulary) or token.is_digit)
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
        words_known=words_you_know,
        percent_words_known=int(
            ((words_you_know / word_count) if word_count > 0 else 0) * 100
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
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb", encoding="utf-8"),
    help="Known Morphs csv from Ankimorphs",
)
def cli_book_complexity(inputfile, pipeline, knownmorphs):
    """Calculate complexity of a single text file and send it to the console"""
    nlp = make_nlp(pipeline)

    known_morph_list = morphs_from_csv(knownmorphs)

    complexity = book_complexity(inputfile, nlp, known_morph_list)

    print(
        tabulate(
            [
                ["Words", complexity.word_count],
                ["Mean word length", complexity.mean_word_length],
                ["Mean words per sentence", complexity.mean_words_per_sentence],
                ["Mean grammar depth", complexity.mean_grammar_depth],
                ["Words known", complexity.words_known],
                ["Percent words known", complexity.percent_words_known],
                ["Complexity score", complexity.overall_score],
            ]
        )
    )


def morphs_from_csv(knownmorphs):
    known_morph_list = set()
    morph_reader = unicodecsv.reader(knownmorphs)
    for row in morph_reader:
        known_morph_list.add(row[1])
    return known_morph_list


@click.command()
@click.argument("inputfolder", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb", encoding="utf-8"),
    help="Known Morphs csv from Ankimorphs",
)
@click.option(
    "--pipeline", help="Name of spacy pipeline to read files"
)  # ru_core_news_sm
@click.option(
    "--outputcsv",
    type=click.File(mode="wb"),
    help="Name of a csv file to put the results",
)
def cli_books_complexity(inputfolder, pipeline, knownmorphs, outputcsv):
    """Calculate the complexity of all text files in a folder, and
    output a CSV with one line per text file"""
    nlp = make_nlp(pipeline)
    known_morph_list = morphs_from_csv(knownmorphs)
    files = glob.glob(inputfolder + "/**/*.txt", recursive=True)
    if outputcsv:
        with alive_progress.alive_bar(
            len(files), bar="bubbles", spinner="classic"
        ) as bar:
            writer = unicodecsv.writer(outputcsv)
            writer.writerow(
                [
                    "File name",
                    "Word count",
                    "Mean word length",
                    "Mean words per sentence",
                    "Mean grammar depth",
                    "Words known",
                    "Percent words known",
                    "Overall Score",
                ]
            )

            for filename in files:
                with open(filename, "r", encoding="utf-8") as file:
                    result = book_complexity(file, nlp, known_morph_list)
                    writer.writerow(
                        [
                            file.name,
                            result.word_count,
                            result.mean_word_length,
                            result.mean_words_per_sentence,
                            result.mean_grammar_depth,
                            result.words_known,
                            result.percent_words_known,
                            result.overall_score,
                        ]
                    )
                bar.text(filename)
                bar()
