from spacy.tokenizer import Tokenizer
from spacy.tokens import Doc
from spacy.language import Language
import spacy

@Language.component("tidy_punctuation")
def tidy_doc_punctuation(doc: Doc) -> Doc:
    '''Retokenize so all punctuation becomes part of its preceding non-punctuation token'''
    spans = []
    for word in doc[:-1]:
        if word.is_punct or not word.nbor(1).is_punct:
            continue
        start = word.i
        end = word.i + 1
        while end < len(doc) and doc[end].is_punct:
            end += 1
        span = doc[start:end]
        spans.append((span, word.tag_, word.lemma_, word.ent_type_))
    with doc.retokenize() as retokenizer:
        for span, tag, lemma, ent_type in spans:
            attrs = {"tag": tag, "lemma": lemma, "ent_type": ent_type}
            retokenizer.merge(span, attrs=attrs)
    return doc

def make_nlp():
    nlp = spacy.load("ru_core_news_sm")
    
    nlp.add_pipe("sentencizer")
    nlp.add_pipe("tidy_punctuation")
    assert isinstance(nlp.tokenizer, Tokenizer)

    return nlp

