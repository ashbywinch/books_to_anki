import spacy
from spacy.tokenizer import Tokenizer

def make_nlp():
    enabled_pipes = {
        "tok2vec"
        "parser",
        "sentencizer"
    }
    nlp = spacy.load("ru_core_news_sm")
    
    nlp.add_pipe("sentencizer")
    assert isinstance(nlp.tokenizer, Tokenizer)

#    for pipe in nlp.component_names:
#        if pipe not in enabled_pipes:
#            nlp.disable_pipe(pipe)

    return nlp

