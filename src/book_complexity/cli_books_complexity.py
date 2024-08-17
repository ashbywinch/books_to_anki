from .book_complexity import get_books_complexity


import click


@click.command()
@click.argument("inputfolder", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--knownmorphs",
    type=click.File(mode="rb"),
    help="Known Morphs csv from Ankimorphs",
)
@click.option(
    "--frequencycsv",
    type=click.File(mode="rb"),
    help="Frequency file for the language used",
)
@click.option(
    "--pipeline", help="Name of spacy pipeline to read files"
)  # ru_core_news_sm
@click.option(
    "--outputfilename",
    type=click.Path(dir_okay=False),
    help="Name of a jsonl file to put the results",
)
def cli_books_complexity(
    inputfolder, pipeline, knownmorphs, frequencycsv, outputfilename
):
    """Calculate the complexity of all text files in a folder, and
    output a CSV with one line per text file"""
    get_books_complexity(
        inputfolder=inputfolder,
        pipeline=pipeline,
        knownmorphs=knownmorphs,
        frequencycsv=frequencycsv,
        outputfilename=outputfilename,
    )
