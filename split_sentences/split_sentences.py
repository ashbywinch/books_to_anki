"""Uses Spacy to intelligently split text into smaller chunks that are likely to be
intelligible without context, grouping words together that are closely related
in the parse tree"""

import bisect

from spacy.tokens import Doc, Span, Token


def are_consecutive(a: Span, b: Span) -> bool:
    """Are these two spans consecutive in the source document"""
    assert a.doc is b.doc
    return (a.start < b.start) and (a.end == b.start)


def merge_spans(doc: Doc, a: Span, b: Span) -> Span:
    """Return a single span containing both consecutive input spans"""
    assert are_consecutive(a, b)
    return Span(doc, a.start, b.end)


def consolidate_spans(doc: Doc, spans: list[Span], max_span_length=None) -> list[Span]:
    """Merge several consecutive smaller spans into larger ones, obeying max_span_length"""
    i = 0
    while i < len(spans):
        if len(spans) <= i + 1:  # nothing left to merge
            return spans

        a, b = spans[i], spans[i + 1]
        too_long_to_merge = max_span_length is not None and (
            len(a.text) + len(b.text) > max_span_length
        )
        if not too_long_to_merge and are_consecutive(a, b):
            spans[i : i + 2] = [merge_spans(doc, a, b)]  # in-place merge
        else:
            i = i + 1


def consolidated_spans_in_tree(
    doc: Doc, root_token: Token, max_span_length=None
) -> list[Span]:
    """Return all the text with a dependency on root_token,
    broken into spans no longer than max_span_length.
    Does a depth first search of the grammar tree, consolidating
    siblings (respecting max_span_length) as it goes."""
    all_spans_in_tree: list[Span] = []

    # accumulate sorted consolidated spans of all children
    for child in root_token.children:
        spans = consolidated_spans_in_tree(
            doc, root_token=child, max_span_length=max_span_length
        )
        for span in spans:
            bisect.insort(all_spans_in_tree, span)

    # insert root span in sorted order and reconsolidate across root and children
    bisect.insort(all_spans_in_tree, Span(doc, root_token.i, root_token.i + 1))
    all_spans_in_tree = consolidate_spans(doc, all_spans_in_tree, max_span_length)

    return all_spans_in_tree


def split_sentence(doc: Doc, sentence: Span, max_span_length: int) -> list[Span]:
    """return all the text from the sentence, 
    broken into spans no longer than max_span_length chars"""
    roots = [token for token in sentence if token.dep_ == "ROOT"]
    assert len(roots) == 1
    return consolidated_spans_in_tree(
        doc, root_token=roots[0], max_span_length=max_span_length
    )
