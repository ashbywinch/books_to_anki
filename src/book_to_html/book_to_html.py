import os
from pathlib import Path
import click
import deepl
import jinja2
from importlib_resources import files

import book_to_html.resources

from book_to_flashcards.book_to_flashcards import (
    generate_cards,
    generate_cards_front_only,
)


@click.command()
@click.argument("inputfile", type=click.File(mode="r", encoding="utf-8"))
@click.option(
    "--pipeline", required=True, help="Name of spacy pipeline to read file"
)  # ru_core_news_sm
@click.option(
    "--lang", help="Code for language that DeepL will translate into e.g. EN-US"
)
@click.option(
    "--outputfolder",
    type=click.Path(exists=True, file_okay=False, writable=True),
    default=os.getcwd(),
    help="Where to put the csv output (defaults to cwd)",
)
@click.option(
    "--maxfieldlen",
    type=click.IntRange(30),
    default=70,
    help="The maximum desired length of a text field (translations may be longer)",
)
@click.option(
    "--translate/--notranslate",
    default=False,
    help="Add translations to file (otherwise dummy translations are used)",
)
@click.option(
    "--deeplkey",
    envvar="DEEPL_KEY",
    help="API key for DeepL (required for translations)",
)
@click.option(
    "--fontsize",
    type=click.IntRange(),
    default=30,
    show_default=True,
    help="Font sized used for text within HTML",
)
def cli_make_book_html(
    inputfile,
    pipeline: str,
    outputfolder: str,
    lang: str,
    maxfieldlen: int,
    translate: False,
    deeplkey: str,
    fontsize: int,
):
    """Take a single text file and generate an HTML file, one card per row"""
    outputfile = Path(outputfolder, Path(inputfile.name).with_suffix(".html").name)
    with open(outputfile, "w", encoding="utf8") as file:

        if translate:
            cards = generate_cards(
                inputfile, pipeline, maxfieldlen, deepl.Translator(deeplkey), lang
            )
        else:
            cards = generate_cards_front_only(inputfile, pipeline, maxfieldlen)

        # populate Jinja templates to create actual html/CSS
        environment = jinja2.Environment()
        css_template_text = (
            files(book_to_html.resources).joinpath("book.css.jinja").read_text()
        )
        css_template = environment.from_string(css_template_text)
        css = css_template.render(font_size=fontsize)

        html_template_text = (
            files(book_to_html.resources).joinpath("book.html.jinja").read_text()
        )
        html_template = environment.from_string(html_template_text)
        html = html_template.render(
            title=Path(inputfile.name).stem, css=css, cards=cards, font_size=fontsize
        )

        file.write(html)
