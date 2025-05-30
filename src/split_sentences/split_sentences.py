"""
Provides functionality to intelligently split text into smaller, contextually coherent chunks.

This module uses spaCy's linguistic annotations (particularly dependency parsing)
to break down text into spans that are more likely to be intelligible without
extensive surrounding context. This is useful for applications like generating
flashcards or creating side-by-side translations where smaller segments are desired.

The main entry point is typically `split_text`, which takes an iterable of spaCy
`Doc` objects (e.g., one `Doc` per line of a larger text) and a `max_span_length`
constraint. It attempts to keep grammatically related words together (by traversing
the dependency tree) while ensuring that the resulting spans do not exceed the
specified maximum character length.

Spans that cross the boundaries of the input `Doc` objects are represented
as `CrossDocSpan` objects, which store their own text and global start/end
character offsets.
"""

import bisect
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from spacy.tokens import Doc, Span, Token # type: ignore


def are_consecutive(a: Span, b: Span) -> bool:
    """Checks if two spaCy Spans are consecutive in the source document.

    Args:
        a: The first span.
        b: The second span.

    Returns:
        True if span 'a' immediately precedes span 'b', False otherwise.
    """
    return (a.start < b.start) and (a.end == b.start)


def merge_spans(span_a: Union[Span, 'CrossDocSpan'], span_b: Union[Span, 'CrossDocSpan']) -> Union[Span, 'CrossDocSpan']:
    """Merges two consecutive spans into a single span.

    If both spans are from the same spaCy Doc, a new spaCy Span is created.
    If they are CrossDocSpans or a mix, a new CrossDocSpan is created,
    concatenating their text.

    Args:
        span_a: The first span.
        span_b: The second span, which must be consecutive to span_a.

    Returns:
        A new Span or CrossDocSpan representing the merged content.

    Raises:
        AssertionError: If the spans are not consecutive or, for spaCy Spans,
                        if they are not from the same Doc.
    """
    assert are_consecutive(span_a, span_b) # type: ignore
    if type(span_a) is Span and type(span_b) is Span: 
        assert span_a.doc is span_b.doc
        # in Spacy the actual text lives in the doc object, so we have to pass the doc around...
        return Span(span_a.doc, span_a.start, span_b.end) 
    # across docs, we store the entire span text in the span object itself, instead of indexing
    # into multiple docs
    return CrossDocSpan(span_a.start, span_b.end, span_a.text_with_ws + span_b.text_with_ws)

def consolidate_spans(
    spans: Iterable[Union[Span, 'CrossDocSpan']], 
    max_span_length: Optional[int] = None
) -> Generator[Union[Span, 'CrossDocSpan'], Any, Any]:
    """Merges consecutive smaller spans from an iterable into larger ones.

    This function iterates through a sequence of spans. If consecutive spans
    can be merged without exceeding `max_span_length` (if provided),
    they are combined. Otherwise, the currently accumulated span is yielded,
    and accumulation starts anew with the current span.

    Args:
        spans: An iterable of Span or CrossDocSpan objects.
        max_span_length: Optional maximum character length for a merged span.
                         If None, spans are merged as long as they are consecutive.

    Yields:
        Consolidated Span or CrossDocSpan objects.
    """
    accumulating_span: Optional[Union[Span, 'CrossDocSpan']] = None
    for span in spans:
        too_long_to_merge = accumulating_span and max_span_length and (
            len(accumulating_span.text_with_ws) + len(span.text_with_ws) > max_span_length
        )
        if accumulating_span is None: 
            accumulating_span = span
        elif (not too_long_to_merge) and are_consecutive(accumulating_span, span): # type: ignore
            accumulating_span = merge_spans(accumulating_span, span) 
        else: 
            yield accumulating_span
            accumulating_span = span

    # Anything left?
    if accumulating_span:
        yield accumulating_span


def consolidated_spans_in_tree(
    doc: Doc, 
    root_token: Token, 
    max_span_length: Optional[int] = None
) -> Generator[Span, Any, Any]:
    """Recursively traverses a dependency subtree and yields consolidated spaCy Spans.

    It performs a depth-first search starting from `root_token`.
    At each level of the tree (starting with the leaves), spans from children
    subtrees are collected, sorted by their start position,
    and then the `root_token` itself (as a span) is inserted. Finally,
    `consolidate_spans` is called on this sorted list to merge adjacent spans
    while respecting `max_span_length`.
    The algorithm is repeated as we move up the tree towards the root.
    This approach aims to keep syntactically related words (e.g. subclauses) together.

    Args:
        doc: The parent spaCy Doc.
        root_token: The root token of the current subtree to process.
        max_span_length: Optional maximum character length for consolidated spans.

    Yields:
        Consolidated spaCy Span objects from the subtree.
    """
    all_spans_in_tree: list[Span] = []

    # accumulate sorted consolidated spans of all children
    for child in root_token.children:
        for span_from_child in consolidated_spans_in_tree(
            doc, root_token=child, max_span_length=max_span_length
        ):
            bisect.insort(all_spans_in_tree, span_from_child)

    # insert root span in sorted order and reconsolidate across root and children
    bisect.insort(all_spans_in_tree, Span(doc, root_token.i, root_token.i + 1))
    yield from consolidate_spans(all_spans_in_tree, max_span_length) # type: ignore


def split_sentence(doc: Doc, sentence: Span, max_span_length: int) -> Generator[Span, Any, Any]:
    """Splits a single sentence (spaCy Span) into smaller, grammatically coherent spans.

    This function identifies the root of the sentence's dependency tree and then
    uses `consolidated_spans_in_tree` to generate spans that are no longer
    than `max_span_length` characters.

    Args:
        doc: The parent spaCy Doc (required by `consolidated_spans_in_tree`).
        sentence: The spaCy Span representing the sentence to split.
        max_span_length: The maximum character length for the output spans.

    Yields:
        Consolidated spaCy Span objects from the sentence.

    Raises:
        AssertionError: If the sentence does not have exactly one ROOT token.
    """
    roots = [token for token in sentence if token.dep_ == "ROOT"]
    assert len(roots) == 1, f"Sentence should have exactly one ROOT. Found {len(roots)} in: '{sentence.text}'"
    yield from consolidated_spans_in_tree(
        doc, root_token=roots[0], max_span_length=max_span_length
    )

def split_from_sentences(doc: Doc, max_span_length: int) -> Generator[Span, Any, Any]:
    """Applies `split_sentence` to all sentences in a single spaCy Doc.

    Args:
        doc: The spaCy Doc to process.
        max_span_length: The maximum character length for spans from each sentence.

    Yields:
        SpaCy Span objects from splitting all sentences in the Doc.
    """
    for sent in doc.sents:
        yield from split_sentence(doc, sent, max_span_length)

def split_sentences(doc: Doc, max_span_length: int) -> Generator[Span, Any, Any]:
    """Splits all sentences in a Doc and then consolidates the resulting spans.

    This first uses `split_from_sentences` to get all fine-grained spans from
    the document's sentences. Then, it applies `consolidate_spans` to merge
    these potentially numerous small spans if they are adjacent and within
    the `max_span_length` limit. This helps in joining small fragments
    that might have been split across sentence parts but can be recombined.

    Args:
        doc: The spaCy Doc to process.
        max_span_length: The maximum character length for the final consolidated spans.

    Yields:
        Consolidated spaCy Span objects from the Doc.
    """
    yield from consolidate_spans(split_from_sentences(doc, max_span_length), max_span_length) # type: ignore

@dataclass
class CrossDocSpan:
    """Represents a text span that may cross boundaries of original Doc objects.

    Unlike spaCy Spans which are tied to a single Doc, CrossDocSpans store
    their own text and use absolute character offsets relative to the beginning
    of the entire multi-document text being processed.

    Attributes:
        start: The starting character offset of the span (globally).
        end: The ending character offset of the span (globally).
        text_with_ws: The text content of the span, including whitespace.
    """
    start: int
    end: int
    text_with_ws: str
    

def split_from_text(docs: Iterable[Doc], max_span_length: int) -> Generator[CrossDocSpan, Any, Any]:
    """Processes an iterable of Docs, yielding CrossDocSpans with global offsets.

    This function iterates through multiple spaCy `Doc` objects (which could
    represent lines or larger chunks of a text). For each `Doc`, it calls
    `split_sentences` to get sentence-level consolidated spans. These spaCy
    Spans are then converted into `CrossDocSpan` objects, adjusting their
    character offsets to be global (cumulative across all processed Docs).

    Args:
        docs: An iterable of spaCy Doc objects.
        max_span_length: The maximum character length passed to `split_sentences`.

    Yields:
        CrossDocSpan objects representing text segments with global offsets.
    """
    doc_base = 0
    # doc_len = 0 # Removed initialization for doc_len

    for doc in docs:
        for span in split_sentences(doc, max_span_length=max_span_length):
            doc_len = span.end_char # type: ignore
            
            yield CrossDocSpan(
                start = doc_base + span.start_char,
                end = doc_base + span.end_char,
                text_with_ws = span.text_with_ws,
            )
        doc_base = doc_base + doc_len

def split_text(docs: Iterable[Doc], max_span_length: int) -> Generator[CrossDocSpan, Any, Any]:
    """Top-level function to split text from multiple Docs into consolidated CrossDocSpans.

    This function first processes an iterable of spaCy `Doc` objects using
    `split_from_text` to generate a sequence of `CrossDocSpan` objects. These
    spans have global character offsets. It then applies `consolidate_spans`
    to this sequence one last time to merge any adjacent `CrossDocSpan` objects
    that are within the `max_span_length` limit.

    This is typically the main function to call for splitting a full text
    (represented as an iterable of Docs) into manageable chunks.

    Args:
        docs: An iterable of spaCy Doc objects (e.g., one per line).
        max_span_length: The maximum character length for the final consolidated spans.

    Yields:
        Consolidated CrossDocSpan objects.
    """
    yield from consolidate_spans(split_from_text(docs, max_span_length), max_span_length) # type: ignore