"""SpaCy pipeline customization for sentence splitting.

This module provides utility functions to create and configure spaCy `Language`
objects (nlp pipelines) tailored for the sentence splitting tasks in this project.
It includes a custom spaCy pipeline component, `tidy_doc_punctuation`,
which modifies tokenization behavior for punctuation.
"""
from spacy.tokenizer import Tokenizer # type: ignore[import-untyped]
from spacy.tokens import Doc
from spacy.language import Language
import spacy

@Language.component("tidy_punctuation")
def tidy_doc_punctuation(doc: Doc) -> Doc:
    """Custom spaCy component to retokenize punctuation with its preceding token.

    This component iterates through the document and merges sequences of punctuation
    with the non-punctuation token that immediately precedes them. For example,
    a sequence like `Token("word") Token(".") Token("!")` would be retokenized into
    a single token `Token("word.!")`.

    The motivation is to keep punctuation attached to the word it belongs to,
    which can be beneficial for subsequent sentence splitting logic by preventing
    punctuation from forming separate, small spans or influencing split points
    in undesirable ways.

    Args:
        doc: The input spaCy `Doc` object.

    Returns:
        The spaCy `Doc` object with modified tokenization for punctuation.
    """
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
            retokenizer.merge(span, attrs=attrs) # type: ignore[arg-type]
    return doc

def make_nlp(pipeline: str) -> Language:
    """Creates and configures a spaCy `Language` object (nlp pipeline).

    This function loads a specified spaCy pipeline and customizes it by:
    1. Excluding components not strictly necessary for this project's sentence
       splitting and complexity analysis tasks (`"lemmatizer"`, `"ner"`, 
       `"attribute_ruler"`), which can improve loading speed and memory usage.
    2. Adding the custom `tidy_doc_punctuation` component to the pipeline to
       modify how punctuation is tokenized.
    
    An assertion is also made to ensure the pipeline's tokenizer is an instance
    of `spacy.tokenizer.Tokenizer`, which is expected for standard pipelines.

    Args:
        pipeline: The name of the base spaCy pipeline to load 
                  (e.g., 'en_core_web_sm', 'ru_core_news_sm').

    Returns:
        A configured spaCy `Language` object.
    """
    nlp = spacy.load(pipeline, exclude=["lemmatizer", "ner", "attribute_ruler"]) 
    nlp.add_pipe("tidy_punctuation")
    assert isinstance(nlp.tokenizer, Tokenizer)

    return nlp

