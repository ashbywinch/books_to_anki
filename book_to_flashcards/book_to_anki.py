import html
from pathlib import Path
import click
import glob
import genanki
import hashlib
from importlib_resources import files
from book_to_flashcards import generate_cards
import book_to_flashcards.resources

class BookNote(genanki.Note):
    @property
    def guid(self):
        # A reasonably stable ID for the card - hash the filename along with the
        # character index of the card text within the file and the card text.
        # It's possible for multiple cards from a file to have the same text
        return genanki.guid_for(self.fields[0], self.fields[1], self.fields[3])

def makeModel() -> genanki.Model:
    return genanki.Model(
        1356306641, 
        "Book Snippet", 
        fields=[
            {'name': 'index_in_file'},
            {'name': 'file'},
            {'name': 'prev'},
            {'name': 'current'},
            {'name': 'next'},
            {'name': 'translation'},
        ],
        templates=[
            {
            'name': 'Card 1',
            'qfmt': files(book_to_flashcards.resources).joinpath('front_template.html').read_text(),
            'afmt': files(book_to_flashcards.resources).joinpath('back_template.html').read_text(),
            },
        ],
        css = files(book_to_flashcards.resources).joinpath('styling.css').read_text())


@click.command()
@click.argument('inputfolder', required=False, type=click.Path(exists=True, file_okay=False))
@click.option('--structure/--nostructure', default=True, show_default=True, help="Structure the deck to match the input folder structure")
@click.option('--filelist', type=click.File(mode="r", encoding="utf-8"), help="name of a file containing specific book filenames to include (one per line)")
@click.option('--pipeline', required=True, help="Name of spacy pipeline to read files") # ru_core_news_sm
@click.option('--lang', help='Code for language that DeepL will translate into e.g. EN-US')
@click.option('--maxfieldlen', type=click.IntRange(30), default = 70, show_default=True, help='The maximum desired length of a text field (translations may be longer)')
@click.option('--translate/--notranslate', default = False, show_default=True, help= 'Add translations to file (otherwise dummy translations are used)')
@click.option('--deeplkey', envvar='DEEPL_KEY', help='API key for DeepL (required for translations)')
@click.option('--ankifile', type=click.File(mode="wb"), required=True, help="Name of an anki .apkg file to put the results")
def cli_books_to_anki(inputfolder, structure, filelist, pipeline, lang, maxfieldlen, translate, deeplkey, ankifile):
    if(filelist):
        text_files = filelist.readlines()
    else:
        text_files = glob.glob(inputfolder + '/**/*.txt', recursive=True)

    model = makeModel()

    decks:list[genanki.Deck] = []

    for filename in text_files:
        if(structure):
            directoryelements = list(Path(filename).parts)[0:-1] # chop off the filename
            directoryelements.append(Path(filename).stem)
            deckname = "::".join(directoryelements)
        else:
            deckname = Path(filename).stem

        deck = genanki.Deck(
            # a reasonably stable ID for this deck - hash the filename
            int(hashlib.sha1(deckname.encode("utf-8")).hexdigest(), 16) % (2 ** 32),
            html.escape(deckname))
        
        with open(filename.strip(), "r", encoding="utf-8") as file:
            for card in generate_cards(file, pipeline, lang, maxfieldlen, translate, deeplkey):
                note = BookNote(
                    model=model,
                    fields=[
                        str(card.index_in_file),
                        html.escape(Path(filename).stem),
                        html.escape(card.prev), 
                        html.escape(card.current), 
                        html.escape(card.next), 
                        html.escape(card.translation)])
                deck.add_note(note)
            decks.append(deck)
    genanki.Package(decks).write_to_file(ankifile)