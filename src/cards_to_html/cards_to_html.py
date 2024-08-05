from collections.abc import Generator
from pathlib import Path
from typing import Any, Callable
import jinja2
from importlib_resources import files

import cards_to_html.resources as resources

from book_to_flashcards.Card import Card


def cards_to_html(
    cards: Generator[Card, Any, Any],
    outputfolder: str,
    bookname: str,
    use_folder_structure: bool,
    fontsize: int,
    on_file_complete: Callable[[], None],
):
    """Take cards and generate HTML files with side by side translation,
    one file for each filename in the card data"""
    if use_folder_structure:
        outputfile = Path(outputfolder, Path(bookname).with_suffix(".html"))
        outputfile.parent.mkdir(exist_ok=True, parents=True)
    else:
        outputfile = Path(outputfolder, Path(bookname).with_suffix(".html").name)
    with open(outputfile, "w", encoding="utf8") as file:

        # populate Jinja templates to create actual html/CSS
        environment = jinja2.Environment()
        css_template_text = files(resources).joinpath("book.css.jinja").read_text()
        css_template = environment.from_string(css_template_text)
        css = css_template.render(font_size=fontsize)

        html_template_text = files(resources).joinpath("book.html.jinja").read_text()
        html_template = environment.from_string(html_template_text)
        html = html_template.render(
            title=bookname, css=css, cards=cards, font_size=fontsize
        )

        file.write(html)
    on_file_complete()


def cards_to_htmls(
    cards: Generator[Card, Any, Any],
    outputfolder: str,
    fontsize: int,
    on_file_complete: Callable[[], None],
):
    # split the cards into chunks for each file
    # send them to html like that
    book: list[Card] = []
    bookname = None
    for card in cards:
        if bookname and bookname != card.filename:
            cards_to_html(
                book,
                outputfolder,
                bookname=bookname,
                use_folder_structure=True,
                fontsize=fontsize,
                on_file_complete=on_file_complete,
            )
            book = []
        bookname = card.filename
        book.append(card)
    if bookname:
        cards_to_html(
            book,
            outputfolder,
            bookname=bookname,
            use_folder_structure=True,
            fontsize=fontsize,
            on_file_complete=on_file_complete,
        )  # last book, assuming there was one
