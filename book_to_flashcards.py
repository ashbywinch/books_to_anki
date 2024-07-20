import os
from pathlib import Path
from split_sentences import make_nlp, split_sentence, tidy_doc_punctuation
import unicodecsv
import click
import deepl

@click.command()
@click.argument('inputfile', type=click.File(mode="r", encoding="utf-8"))
@click.option('--lang', help='Code for language to translate into e.g. EN-US')
@click.option('--outputfolder', type=click.Path(exists=True, file_okay=True, writable=True), default=os.getcwd(), help='Where to put the csv output')
@click.option('--maxfieldlen', type=click.IntRange(30), default = 70, help='The maximum desired length of a text field (translations may be longer)')
@click.option('--translate/--notranslate', default = False, help= 'Add translations to file (otherwise dummy translations are used)')
@click.option('--deeplkey', envvar='DEEPL_KEY', help='API key for DeepL (required for translations)')
def make_flashcard_csv(inputfile, outputfolder, lang: str, maxfieldlen: int, translate: False, deeplkey: str):
    nlp = make_nlp()
    if(translate):
        translator = deepl.Translator(deeplkey)

    outputfile = Path(outputfolder, Path(inputfile.name).with_suffix('.csv').name)
    with open(outputfile, "wb") as csvfile:
        writer = unicodecsv.writer(csvfile, delimiter=';')
        
        prev_span = current_span = None
        sentence_id = 0
        for line in inputfile:
            docs = nlp.pipe([line.strip()])
            for doc in docs:
                doc = tidy_doc_punctuation(doc)
                for s in doc.sents:
                    for next_span in split_sentence(doc, s, max_span_length = maxfieldlen):
                        if(current_span):
                            if(translate):
                                translation = translator.translate_text(current_span.text, target_lang=lang)
                            else:
                                translation = "Translation placeholder"
                        
                            writer.writerow((sentence_id,prev_span.text if prev_span else '', current_span.text, next_span.text, translation))
                        prev_span = current_span
                        current_span = next_span
                        sentence_id = sentence_id + 1

        # write the very last row, which has no next span
        writer.writerow((sentence_id, prev_span.text, current_span.text, '', translation))

