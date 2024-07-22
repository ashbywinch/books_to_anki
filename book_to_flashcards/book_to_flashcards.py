import os
from pathlib import Path
from split_sentences import make_nlp, split_sentence
import unicodecsv
import click
import deepl
from dataclasses import dataclass

@dataclass
class Card:
    index_in_file: int
    prev: str
    current: str
    next: str
    translation: str

def generate_cards(inputfile, pipeline, lang, maxfieldlen, translate, deeplkey):
    nlp = make_nlp(pipeline)
    if(translate):
        translator = deepl.Translator(deeplkey)
    
    prev_span = current_span = None
    cumulative_chars = current_sentence_base = 0
    for line in inputfile:
        docs = nlp.pipe([line.strip()])
       
        for doc in docs:
            for s in doc.sents:
                for next_span in split_sentence(doc, s, max_span_length = maxfieldlen):
                    if(current_span):
                        if(translate):
                            translation = str(translator.translate_text(current_span.text, target_lang=lang))
                        else:
                            translation = ""
                        yield Card(current_sentence_base + current_span.start_char, prev_span.text if prev_span else '', current_span.text, next_span.text, translation)
                    prev_span = current_span
                    current_span = next_span
                    if(prev_span and current_span.doc is not prev_span.doc): # once current_span moves from one line to the next
                        current_sentence_base = cumulative_chars

            break # there was only one doc, hopefully!
        cumulative_chars = cumulative_chars + len(line.strip()) # how many chars to start of current line        

    if(translate):
        # translate and write the very last row, which has no next span
        translation = str(translator.translate_text(current_span.text, target_lang=lang))
        yield Card(cumulative_chars + current_span.start_char, prev_span.text, current_span.text, '', translation)

@click.command()
@click.argument('inputfile', type=click.File(mode="r", encoding="utf-8"))
@click.option('--pipeline', help="Name of spacy pipeline to read file") # ru_core_news_sm
@click.option('--lang', help='Code for language that DeepL will translate into e.g. EN-US')
@click.option('--outputfolder', type=click.Path(exists=True, file_okay=False, writable=True), default=os.getcwd(), help='Where to put the csv output (defaults to cwd)')
@click.option('--maxfieldlen', type=click.IntRange(30), default = 70, help='The maximum desired length of a text field (translations may be longer)')
@click.option('--translate/--notranslate', default = False, help= 'Add translations to file (otherwise dummy translations are used)')
@click.option('--deeplkey', envvar='DEEPL_KEY', help='API key for DeepL (required for translations)')
def cli_make_flashcard_csv(inputfile, pipeline: str, outputfolder: str, lang: str, maxfieldlen: int, translate: False, deeplkey: str):
    
    outputfile = Path(outputfolder, Path(inputfile.name).with_suffix('.csv').name)
    with open(outputfile, "wb") as csvfile:
        writer = unicodecsv.writer(csvfile, delimiter=';')
        for card in generate_cards(inputfile, pipeline, lang, maxfieldlen, translate, deeplkey):
            writer.writerow(card.index_in_file, card.prev, card.current, card.next, card.translation)

