"""Take a text file containing human language and turn it into a flashcard data structure
with translations in another language"""

from collections.abc import Generator
import glob
from itertools import chain, islice
import os
from typing import Any

import alive_progress
import click
import deepl
from unicodecsv import UnicodeWriter, UnicodeReader

from book_to_flashcards.Card import Card
from book_to_flashcards.book_to_anki import books_to_anki
from book_to_html.book_to_html import books_to_html
from split_sentences import make_nlp, split_sentence


class Progress:
    """this class lets us separate progress bar initialisation from the code where we discover how many steps there are"""

    bar = None
    num_steps = 0

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        self.bar()


__progress = Progress()


def make_progress_bar(num_steps: int):
    return alive_progress.alive_bar(num_steps, bar="bubbles", spinner="classic")


def generate_cards_front_only(
    inputfile, pipeline, maxfieldlen
) -> Generator[Card, Any, Any]:
    """Take a single text file and produce a set of flash cards
    containing chunks not longer than maxfieldlen, with no translations included
    (so, just the front)
    This is much quicker and avoids 'using up' a DeepL API key if you don't need it"""
    nlp = make_nlp(pipeline)

    prev_span = current_span = None
    cumulative_chars = current_sentence_base = 0
    with open(inputfile, mode="r", encoding="utf-8") as file:
        for line in file:
            docs = nlp.pipe([line.strip()])

            for doc in docs:
                for s in doc.sents:
                    for next_span in split_sentence(
                        doc, s, max_span_length=maxfieldlen
                    ):
                        if current_span:
                            yield Card(
                                inputfile,
                                current_sentence_base + current_span.start_char,
                                prev_span.text if prev_span else "",
                                current_span.text,
                                next_span.text,
                                "",
                            )
                        prev_span = current_span
                        current_span = next_span
                        if (
                            prev_span and current_span.doc is not prev_span.doc
                        ):  # once current_span moves from one line to the next
                            current_sentence_base = cumulative_chars

                break  # there was only one doc, hopefully!
            # how many chars to start of current line?
            cumulative_chars = cumulative_chars + len(line.strip())

        yield Card(
            inputfile,
            cumulative_chars + current_span.start_char,
            prev_span.text if prev_span else None,
            current_span.text,
            "",
            "",
        )


def chunks(iterable, size=10):
    iterator = iter(iterable)
    for first in iterator:
        yield chain([first], islice(iterator, size - 1))


def translate_cards(cards, translator, lang):
    # batch up all the translations, we don't want a round trip per card
    for chunk in chunks(cards, 100):
        # get all the translations
        translations = translator.translate_text(
            [card.current for card in chunk], target_lang=lang
        )
        # put the translations back in the cards and return
        for card, translation in zip(cards, translations):
            card.translation = translation
            yield card


@click.group(chain=True)
def cli_make_flashcards():
    pass


@cli_make_flashcards.result_callback()
def process_pipeline(processors):
    """Chain generators for each command into a pipeline"""
    with make_progress_bar(__progress.num_steps) as bar:
        __progress.bar = bar
        iterator = None
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


@click.argument("inputfile", type=click.File(mode="rb"))
@cli_make_flashcards.command()
def from_csv(
    inputfile,
):
    def processor(iterator) -> Generator[list[Card], Any, Any]:
        with open(inputfile, mode="rb") as input:
            csvreader = UnicodeReader(input)
            cards: list[Card] = []
            for index_in_file, prev, current, next, translation in csvreader:
                cards.append(
                    Card(inputfile, index_in_file, prev, current, next, translation)
                )
        yield cards

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
        books_to_anki(
            iterator,
            structure=True,
            fontsize=fontsize,
            ankifile=outputfile,
            on_file_complete=__progress,
        )

    return processor


@click.option(
    "--outputfolder",
    type=click.Path(exists=True, file_okay=False, writable=True),
    default=os.getcwd(),
    help="Where to put the html output (defaults to cwd)",
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
        books_to_html(iterator, outputfolder, on_file_complete=__progress)

    return processor


@click.argument(
    "outputfile",
    type=click.Path(dir_okay=False, writable=True),
    default="flashcards.csv",
)
@cli_make_flashcards.command()
def to_csv(outputfile):
    def processor(iterator: Generator[Card]):
        with open(outputfile, mode="wb") as file:
            writer = UnicodeWriter(file)
            filename = None
            for card in iterator:
                writer.writerow(
                    [
                        card.filename,
                        card.index_in_file,
                        card.prev,
                        card.current,
                        card.next,
                        card.translation,
                    ]
                )
                if card.filename != filename:
                    __progress()
                    filename = card.filename

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
            for card in generate_cards_front_only(
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


# generate-cards from-text input.txt pipeline "ru_core" translate output-sidebyside output.html
