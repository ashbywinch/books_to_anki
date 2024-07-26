from spacy.tokens import Token, Doc, Span


class ComplexityCalculator:
    __cumulative_value: int = 0

    def __init__(self, op=lambda x, y: x + y):
        self.op = op

    def read(self, doc: Doc):
        self.__cumulative_value = self.op(self.__cumulative_value, self.doc_value(doc))

    def doc_value(self, doc: Doc) -> int:
        raise NotImplementedError()

    def value(self) -> int:
        return self.__cumulative_value


class ComplexityRatio:
    def __init__(
        self,
        name,
        numerator: ComplexityCalculator,
        denominator: ComplexityCalculator,
        percentage: bool = False,
    ):
        self.name = name
        self.numerator = numerator
        self.denominator = denominator
        self.percentage = percentage

    def value(self) -> int:
        ratio = (
            self.numerator.value() / self.denominator.value()
            if self.denominator.value() > 0
            else 0
        )
        return int(ratio * 100) if self.percentage else round(ratio, 1)


class WordCountComplexityCalculator(ComplexityCalculator):
    name = "Word Count"

    def doc_value(self, doc: Doc):
        return sum(1 for token in doc if not token.is_punct and not token.is_space)


class SentenceCountComplexityCalculator(ComplexityCalculator):
    name = "Sentence Count"

    def doc_value(self, doc: Doc) -> int:
        return sum(1 for dummy in doc.sents)


class CumulativeWordLengthComplexityCalculator(ComplexityCalculator):
    name = "Cumulative Word Length"

    def doc_value(self, doc: Doc) -> int:
        return sum(
            len(token.text)
            for token in doc
            if not token.is_punct and not token.is_space
        )


class CumulativeGrammarDepthComplexityCalculator(ComplexityCalculator):
    name = "Cumulative Grammar Depth"

    def grammar_depth(self, root_token: Token):
        """The depth of the grammatical tree, starting with root_token as the root of the tree"""

        return 1 + max(
            (self.grammar_depth(child) for child in root_token.children), default=0
        )

    def sentence_grammar_depth(self, sent: Span) -> int:
        roots = [token for token in sent if token.dep_ == "ROOT"]
        assert len(roots) == 1
        return self.grammar_depth(roots[0])

    def doc_value(self, doc: Doc) -> int:
        return sum(self.sentence_grammar_depth(sent) for sent in doc.sents)


class WordsKnownComplexityCalculator(ComplexityCalculator):
    name = "Words Known"

    def __init__(self, vocabulary: set[str]):
        super().__init__()
        self.vocabulary = vocabulary

    def doc_value(self, doc: Doc) -> int:
        return sum(
            1 for token in doc if ((token.text in self.vocabulary) or token.is_digit)
        )


class VocabularyLevelComplexityCalculator(ComplexityCalculator):
    name = "Vocabulary level"

    def __init__(self, frequency: dict[str, int], levels: list[range]):
        super().__init__(max)
        self.frequency = frequency
        self.levels = levels

    def token_level(self, token: Token) -> int:
        "Return the correct vocabulary level that reflects the frequency of this token"

        token_frequency = self.frequency.get(token.text.lower(), 0)
        return next(
            (i for i, range in enumerate(self.levels) if token_frequency in range),
            0,
        )

    def doc_value(self, doc: Doc) -> int:
        # what is the vocab level of this doc?
        # let's say it's the level where all the vocab in the doc is at or below the level
        return max((self.token_level(token) for token in doc), default=0)
