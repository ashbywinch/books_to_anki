"""Uses Spacy to intelligently split text into smaller chunks that are likely to be
intelligible without context, grouping words together that are closely related
in the parse tree"""

import bisect
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Iterable

from spacy.tokens import Doc, Span, Token


def are_consecutive(a, b) -> bool:
    """Are these two spans consecutive in the source document"""
    return (a.start < b.start) and (a.end == b.start)


def merge_spans(span_a, span_b):
    """Return a single span containing both consecutive input spans"""
    assert are_consecutive(span_a, span_b)
    if type(span_a) is Span and type(span_b) is Span: 
        assert span_a.doc is span_b.doc
        # in Spacy the actual text lives in the doc object, so we have to pass the doc around...
        return Span(span_a.doc, span_a.start, span_b.end) 
    # across docs, we store the entire span text in the span object itself, instead of indexing
    # into multiple docs
    return CrossDocSpan(span_a.start, span_b.end, span_a.text_with_ws + span_b.text_with_ws)

def consolidate_spans(spans, max_span_length=None):
    """Merge several consecutive smaller spans into larger ones, obeying max_span_length"""
    accumulating_span = None
    for span in spans:
        too_long_to_merge = accumulating_span and max_span_length and (
            len(accumulating_span.text_with_ws) + len(span.text_with_ws) > max_span_length
        )
        if accumulating_span is None: 
            accumulating_span = span
        elif (not too_long_to_merge) and are_consecutive(accumulating_span, span):
            accumulating_span = merge_spans(accumulating_span, span) 
        else: 
            yield accumulating_span
            accumulating_span = span

    # Anything left?
    if accumulating_span:
        yield accumulating_span


def consolidated_spans_in_tree(
    doc: Doc, root_token: Token, max_span_length=None
) -> Generator[Span, Any, Any]:
    """Return all the text with a dependency on root_token,
    broken into spans no longer than max_span_length.
    Does a depth first search of the grammar tree, consolidating
    siblings (respecting max_span_length) as it goes.
    This attempts to keep chunks of syntax tree together as much as possible."""
    all_spans_in_tree: list[Span] = []

    # accumulate sorted consolidated spans of all children
    for child in root_token.children:
        for span in consolidated_spans_in_tree(
            doc, root_token=child, max_span_length=max_span_length
        ):
            bisect.insort(all_spans_in_tree, span)

    # insert root span in sorted order and reconsolidate across root and children
    bisect.insort(all_spans_in_tree, Span(doc, root_token.i, root_token.i + 1))
    yield from consolidate_spans(all_spans_in_tree, max_span_length)


def split_sentence(doc: Doc, sentence: Span, max_span_length: int) -> Generator[Span, Any, Any]:
    """return all the text from the sentence, 
    broken into spans no longer than max_span_length chars"""
    roots = [token for token in sentence if token.dep_ == "ROOT"]
    assert len(roots) == 1
    yield from consolidated_spans_in_tree(
        doc, root_token=roots[0], max_span_length=max_span_length
    )

def split_from_sentences(doc: Doc, max_span_length: int) -> Generator[Span, Any, Any]:
    for sent in doc.sents:
        yield from split_sentence(doc, sent, max_span_length)

def split_sentences(doc: Doc, max_span_length: int) -> Generator[Span, Any, Any]:
    """Now we consolidate across sentences in one Doc (i.e. one line)"""
    yield from consolidate_spans(split_from_sentences(doc, max_span_length), max_span_length)

@dataclass
class CrossDocSpan:
    start: int
    end: int
    text_with_ws: str
    

def split_from_text(docs: Iterable[Doc], max_span_length: int) -> Generator[CrossDocSpan, Any, Any]:
    """Consolidate across a multi line document consisting of several Doc objects"""
    doc_base = 0

    for doc in docs:
        for span in split_sentences(doc, max_span_length=max_span_length):
            doc_len = span.end_char
            
            yield CrossDocSpan(
                start = doc_base + span.start_char,
                end = doc_base + span.end_char,
                text_with_ws = span.text_with_ws,
            )
        doc_base = doc_base + doc_len

def split_text(docs: Iterable[Doc], max_span_length: int) -> Generator[CrossDocSpan, Any, Any]:
    yield from consolidate_spans(split_from_text(docs, max_span_length), max_span_length)