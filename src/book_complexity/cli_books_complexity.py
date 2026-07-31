from __future__ import annotations

"""Command-line interface for batch processing book complexity.

This module provides a CLI using Click to calculate language complexity metrics
for all .txt files within a specified folder. It leverages the 
`get_books_complexity` function from the `book_complexity.book_complexity` module.
"""
import io  # For type hinting Click file objects

import click

from .book_complexity import get_books_complexity


@click.command()
@click.argument("inputfolder", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb"),
    help="Path to a CSV file of known morphs (e.g., from AnkiMorphs). Expected format: one morph per line in the second column.",
)
@click.option(
    "--frequencycsv",
    type=click.File(mode="rb"),
    help="Path to a CSV file containing word frequencies (e.g., lemma,inflection per line). Header expected and skipped.",
)
@click.option(
    "--pipeline", 
    required=True, # Making pipeline required as it's essential
    help="Name of spaCy pipeline to use (e.g., 'en_core_web_sm', 'ru_core_news_sm')."
) 
@click.option(
    "--outputfilename",
    type=click.Path(dir_okay=False),
    required=True, # Output file should be specified
    help="Name/path of the JSONL file to store the results.",
)
@click.option(
    "--remove-title-suffix-after",
    help="Optional string. If provided, book titles (derived from filenames) will be trimmed at the first occurrence of this string."
)
@click.option(
    "--small-sample-size-cutoff",
    type=int,
    default=250,
    help="Word count threshold below which vocabulary level metrics are not calculated."
)
def cli_books_complexity(
    inputfolder: str, 
    pipeline: str, 
    outputfilename: str, 
    knownmorphs: io.BytesIO | None,
    frequencycsv: io.BytesIO | None,
    remove_title_suffix_after: str | None,
    small_sample_size_cutoff: int
):
    """Calculate the complexity of all text files in a folder, and
    output a CSV with one line per text file"""
    get_books_complexity(
        inputfolder=inputfolder,
        pipeline=pipeline,
        knownmorphs_file=knownmorphs,
        frequencycsv_file=frequencycsv,
        outputfilename=outputfilename,
        remove_title_suffix_after=remove_title_suffix_after,
        small_sample_size_cutoff=small_sample_size_cutoff
    )
