from collections.abc import Generator
from pathlib import Path
from typing import Any, Callable
import jinja2
from importlib_resources import files

import book_to_html.resources

from book_to_flashcards.Card import Card


def books_to_html(
    cards: Generator[Card, Any, Any],
    outputfolder: str,
    bookname: str,
    fontsize: int,
    on_file_complete: Callable[[], None],
):
    """Take a single text file and generate an HTML file, one card per row"""
    outputfile = Path(outputfolder, Path(bookname).with_suffix(".html").name)
    with open(outputfile, "w", encoding="utf8") as file:

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
            title=bookname, css=css, cards=cards, font_size=fontsize
        )

        file.write(html)
