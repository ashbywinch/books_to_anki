"""Take a text file containing human language and turn it into a flashcard data structure
with translations in another language"""

from collections.abc import Generator
import glob
import os
import sys
from typing import Any

import alive_progress  # type: ignore
import click
import deepl

from book_to_flashcards.Progress import Progress

from .cards_from_csv import cards_from_csv
from .Card import Card, cards_to_csv
from .cards_to_anki import cards_to_anki
from .cards_untranslated_from_file import cards_untranslated_from_file
from .translate_cards import ReverseTextTranslator, translate_cards
from cards_to_html import cards_to_html


__progress = Progress()


def make_progress_bar(num_steps: int):
    return alive_progress.alive_bar(num_steps, bar="bubbles", spinner="classic")


@click.group(chain=True)
def cli_make_flashcards():
    pass


@cli_make_flashcards.result_callback()
def process_pipeline(processors):
    """Chain generators for each command into a pipeline"""
    iterator = None
    # Don't do progress bar if nobody can see it
    # Non tty outputs can't always handle UTF-8
    if sys.stdout.isatty():
        with make_progress_bar(__progress.num_steps) as bar:
            __progress.bar = bar

            for processor in processors:
                iterator = processor(iterator)
    else:
        for processor in processors:
            iterator = processor(iterator)


@click.argument("inputfile", type=click.Path(readable=True, dir_okay=False))
@cli_make_flashcards.command()
def from_text(
    inputfile,
):
    def processor(iterator):
        yield inputfile

    return processor


@click.argument("inputfile", type=click.Path(dir_okay=False, exists=True))
@cli_make_flashcards.command()
def from_csv(
    inputfile,
):
    def processor(iterator) -> Generator[Card, Any, Any]:
        for card in cards_from_csv(inputfile):
            yield card

    return processor


@click.argument(
    "inputfolder",
    type=click.Path(exists=True, file_okay=False),
)
@cli_make_flashcards.command()
def from_folder(inputfolder):
    files = glob.glob(inputfolder + "/**/*.txt", recursive=True)
    # It's a global variable. I don't know how to get rid of it.
    # The click framework doesn't have a way to pass progress around
    # chained commands
    global __progress
    __progress.num_steps = len(files)

    def processor(iterator) -> Generator[str, Any, Any]:
        for fn in files:
            yield fn

    return processor


@click.argument(
    "outputfile", type=click.Path(dir_okay=False, writable=True), default=os.getcwd()
)
@click.option(
    "--fontsize",
    type=click.IntRange(),
    default=30,
    show_default=True,
    help="Font sized used for card text within Anki",
)
@cli_make_flashcards.command()
def to_anki(outputfile, fontsize):
    def processor(iterator):
        cards_to_anki(
            iterator,
            structure=True,
            fontsize=fontsize,
            ankifile=outputfile,
            on_file_complete=__progress,
        )

    return processor


@click.argument(
    "outputfolder",
    type=click.Path(exists=True, file_okay=False, writable=True),
    default=os.getcwd(),
)
@click.option(
    "--fontsize",
    type=click.IntRange(),
    default=30,
    show_default=True,
    help="Font sized used for card text in output",
)
@cli_make_flashcards.command()
def to_sidebyside(outputfolder, fontsize):

    def processor(iterator):
        cards_to_html.cards_to_htmls(
            iterator,
            outputfolder=outputfolder,
            fontsize=fontsize,
            on_file_complete=__progress,
        )

    return processor


@click.argument(
    "outputfile",
    type=click.Path(dir_okay=False, writable=True),
    default="flashcards.csv",
)
@cli_make_flashcards.command()
def to_csv(outputfile):
    def processor(iterator: Generator[Card]):
        cards_to_csv(iterator, outputfile, __progress)

    return processor


@click.argument("pipeline", required=True)  # ru_core_news_sm
@click.option(
    "--maxfieldlen",
    type=click.IntRange(30),
    default=70,
    help="The maximum desired length of a text field (translations may be longer)",
)
@cli_make_flashcards.command()
def pipeline(pipeline, maxfieldlen):
    def processor(iterator: Generator[str]) -> Generator[Card]:
        for filename in iterator:
            for card in cards_untranslated_from_file(
                inputfile=filename, pipeline=pipeline, maxfieldlen=maxfieldlen
            ):
                yield card

    return processor


@click.option(
    "--lang", help="Code for language that DeepL will translate into e.g. EN-US"
)
@click.option(
    "--deeplkey",
    envvar="DEEPL_KEY",
    help="API key for DeepL (required for translations)",
)
@cli_make_flashcards.command()
def translate(lang, deeplkey):
    def processor(iterator) -> Generator[Card]:
        translator = deepl.Translator(deeplkey)
        for card in translate_cards(iterator, translator, lang):
            yield card

    return processor


@cli_make_flashcards.command()
def dummy_translate():
    def processor(iterator) -> Generator[Card]:
        translator = ReverseTextTranslator()
        for card in translate_cards(iterator, translator, "dummy"):
            yield card

    return processor


# generate-cards from-text input.txt pipeline "ru_core" translate output-sidebyside output.html
