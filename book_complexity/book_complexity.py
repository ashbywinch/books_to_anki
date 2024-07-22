from dataclasses import dataclass
from typing import Generator
import spacy
import click
from spacy.tokens import Token
from spacy.symbols import *
import glob
import unicodecsv

from tabulate import tabulate

def make_nlp(pipeline: str):
    return spacy.load(pipeline, exclude=["lemmatizer", "ner", "attribute_ruler"])


def is_empty(generator:Generator):
    for i in generator:
        return False
    return True

@dataclass
class Complexity:
    word_count: int
    mean_grammar_depth: int
    mean_word_length: int
    mean_words_per_sentence: int
    overall_score: int

def grammar_depth(root_token:Token):
    if(is_empty(root_token.children)):
        return 1
    else:
        return max([grammar_depth(child) for child in root_token.children]) + 1
    
def book_complexity(inputfile, nlp) -> Complexity:
    
    sents_count = 0
    word_count = 0
    cumulative_word_length = 0
    cumulative_grammar_depth = 0

    for line in inputfile:
        docs = nlp.pipe([line.strip()])
        for doc in docs:
            sents_count = sents_count + sum(1 for dummy in doc.sents)
            word_count = word_count + sum(1 for token in doc if not token.is_punct and not token.is_space)
            cumulative_word_length = cumulative_word_length + sum(len(token.text) for token in doc if not token.is_punct and not token.is_space)
            for sent in doc.sents:
                roots = [token for token in sent if token.dep_ == "ROOT"]
                assert(len(roots) == 1)
                cumulative_grammar_depth = cumulative_grammar_depth + grammar_depth(roots[0])             

    complexity = Complexity (
        word_count = word_count,
        mean_words_per_sentence = int(word_count / sents_count) if sents_count > 0 else 0,
        mean_word_length = int(cumulative_word_length / word_count) if word_count > 0 else 0,
        mean_grammar_depth = round(cumulative_grammar_depth / sents_count, 1) if sents_count > 0 else 0,
        overall_score = 0
    )
    complexity.overall_score = complexity.mean_words_per_sentence * complexity.mean_word_length * complexity.mean_grammar_depth
    return complexity

@click.command()
@click.argument('inputfile', type=click.File(mode="r", encoding="utf-8"))
@click.option('--pipeline', help="Name of spacy pipeline to read file") # ru_core_news_sm
def cli_book_complexity(inputfile, pipeline):
    nlp = make_nlp(pipeline)

    complexity = book_complexity(inputfile, nlp)
    print(f"Complexity of text file {inputfile.name}")
    
    print(tabulate([
             ["Words", complexity.word_count],
             ["Mean word length", complexity.mean_word_length],
             ["Mean words per sentence",complexity.mean_words_per_sentence],
             ["Mean grammar depth", complexity.mean_grammar_depth]
             ["Complexity score", complexity.overall_score]
             ]))
    
@click.command()
@click.argument('inputfolder', type=click.Path(exists=True, file_okay=False))
@click.option('--pipeline', help="Name of spacy pipeline to read files") # ru_core_news_sm
@click.option('--outputcsv', type=click.File(mode="wb"), help="Name of a csv file to put the results")
def cli_books_complexity(inputfolder, pipeline, outputcsv):
    nlp = make_nlp(pipeline)

    files = glob.glob(inputfolder + '/**/*.txt', recursive=True)
    if(outputcsv):
        writer = unicodecsv.writer(outputcsv)
        for filename in files:
            with open(filename, "r", encoding="utf-8") as file:
                result = book_complexity(file, nlp)
                writer.writerow([
                    file.name, 
                    result.word_count, 
                    result.mean_word_length, 
                    result.mean_words_per_sentence, 
                    result.mean_grammar_depth,
                    result.overall_score])
    