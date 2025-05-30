"""Tests for book_complexity module"""

from glob import glob

from book_complexity import get_book_complexity, make_nlp
from book_complexity import ComplexityCalculators
from book_complexity.book_complexity import (
    VocabLevelCalculator,
    get_complexities,
    DEFAULT_SMALL_SAMPLE_SIZE_CUTOFF
)
import pytest

from book_complexity.vocabulary_levels import VocabLevels


@pytest.fixture()
def ru_nlp():
    yield make_nlp("ru_core_news_sm")


@pytest.fixture()
def en_nlp():
    yield make_nlp("en_core_web_sm")


@pytest.fixture()
def complexity(ru_nlp):
    long_strings = [
        """Дедушка поцеловал Лидиньку, а она опрометью побежала к Даше, отдала ей рубль 
            и попросила разменять другой, чтобы снести два гривенника бедному хромому.""",
        """Дедушка Ириней очень любил маленьких детей, т.е. таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку""",
    ]
    yield get_book_complexity(long_strings, ru_nlp)


class TestBookComplexityOnMultipleLongerStrings:

    def test_word_count_long(self, complexity):
        assert complexity["Word Count"] == 52

    def test_sentence_count_long(self, complexity):
        assert complexity["Sentence Count"] == 2

    def test_mean_grammar_depth_long(self, complexity):
        assert complexity["Mean Grammar Depth"] == 6.5

    def test_mean_word_length_long(self, complexity):
        assert complexity["Mean Word Length"] == 5.3

    def test_known_words(self, en_nlp):
        teststrings = ["Bob likes green peas"]
        vocabulary = {"likes", "peas"}
        complexity = get_book_complexity(teststrings, en_nlp, vocabulary=vocabulary)

        assert complexity["Words Known"] == 2
        assert complexity["Percent Words Known"] == 50

    def simple_test_vocabulary_level(self):
        frequencies = {"peas": 500, "likes": 20}
        levels = [range(0, 400), range(400, 1000)]
        calculators = ComplexityCalculators()
        calculators.add(VocabLevelCalculator(VocabLevels(frequencies, levels)))

        calculators.get_results()

    def test_vocabulary_level_basic(self, en_nlp):
        frequencies = {"peas": 500, "likes": 20}
        levels = { 'A1':range(0, 400), 'A2':range(400, 1000)}
        teststrings = ["Bob likes green peas"] # 4 words

        complexity = get_book_complexity(
            teststrings, en_nlp, VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=5 # 4 words < 5, so should be cut off
        )

        assert complexity["Vocab Level"] == ""

    def test_vocabulary_level_percentile(self, en_nlp):
        frequencies = {"peas": 500, "likes": 20, "supercalifragilistic": 2000}
        levels = { 'A1':range(0, 400), 'A2':range(400, 1000), 'B1': range(1000, 5000)}

        teststrings = ["Bob likes green peas " * 5 + " supercalifragilistic"] # 21 words

        complexity = get_book_complexity(
            teststrings, en_nlp, vocab_levels=VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=10 # 21 words >= 10, should calculate
        )
        # Calculation: {'A1': 15, 'A2': 5, 'B1': 1}. 95th percentile of 21 words is 19.95th word -> A2
        assert complexity["Vocab Level"] == 'A2'

    def test_vocabulary_level_A1(self, en_nlp):
        frequencies = {"apple": 50, "banana": 60, "cherry": 70, "date": 80, "elderberry": 90, "fig": 100, "grape": 110, "honeydew": 120, "kiwi": 130, "lemon": 140, "mango": 150} # All A1
        levels = {'A1': range(0, 400), 'A2': range(400, 1000), 'B1': range(1000, 5000)}
        teststrings = ["Apple banana cherry date elderberry fig grape honeydew kiwi lemon mango."] # 11 words
        complexity = get_book_complexity(
            teststrings, en_nlp, vocab_levels=VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=10 # 11 words >= 10, should calculate
        )
        # Calculation: {'A1': 11}. 95th percentile of 11 words is 10.45th word -> A1
        assert complexity["Vocab Level"] == 'A1'

    def test_vocabulary_level_B1(self, en_nlp):
        frequencies = {"persimmon": 1500, "boysenberry": 1600, "lingonberry": 1700, "mulberry": 1800, "nectarine": 1900, "olive": 2000, "papaya": 2100, "peach": 2200, "pear": 2300, "pineapple": 2400, "plum": 2500} # All B1
        levels = {'A1': range(0, 400), 'A2': range(400, 1000), 'B1': range(1000, 5000)}
        teststrings = ["Persimmon boysenberry lingonberry mulberry nectarine olive papaya peach pear pineapple plum."] # 11 words
        complexity = get_book_complexity(
            teststrings, en_nlp, vocab_levels=VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=10 # 11 words >= 10, should calculate
        )
        # Calculation: {'B1': 11}. 95th percentile of 11 words is 10.45th word -> B1
        assert complexity["Vocab Level"] == 'B1'

    def test_vocabulary_level_empty_string_input(self, en_nlp):
        frequencies = {"apple": 50}
        levels = {'A1': range(0, 400)}
        teststrings = [""] # 0 words
        complexity = get_book_complexity(
            teststrings, en_nlp, vocab_levels=VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=1 # 0 words < 1, should be cut off
        )
        assert complexity["Word Count"] == 0
        assert complexity["Vocab Level"] == "" # Due to small_sample_size_cutoff

    def test_vocabulary_level_empty_list_input(self, en_nlp):
        frequencies = {"apple": 50}
        levels = {'A1': range(0, 400)}
        teststrings = [] # 0 words
        complexity = get_book_complexity(
            teststrings, en_nlp, vocab_levels=VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=1 # 0 words < 1, should be cut off
        )
        assert complexity["Word Count"] == 0
        assert complexity["Vocab Level"] == "" # Due to small_sample_size_cutoff

    def test_vocabulary_level_no_words_in_frequency_list(self, en_nlp):
        frequencies = {"known": 100, "words": 200} # A1
        levels = {'A1': range(0, 400), 'A2': range(400, 1000)}
        # Text has 11 words
        teststrings = ["Xyz Abc Qwerty Rty Uio Plk Mnb Vcx Zaq Wsx Edc."]
        complexity = get_book_complexity(
            teststrings, en_nlp, vocab_levels=VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=10 # 11 words >= 10, should calculate
        )
        # All words are unknown (default to 'A1'). {'A1': 11}. 95th percentile is 'A1'.
        assert complexity["Vocab Level"] == 'A1'

    def test_vocabulary_level_just_above_cutoff(self, en_nlp):
        # 11 words
        frequencies = {"apple": 50, "banana": 60, "cherry": 70, "date": 80, "elderberry": 90, "fig": 100, "grape": 110, "honeydew": 120, "kiwi": 130, "lemon": 140, "mango": 500} # Most A1, one A2 ("mango")
        levels = {'A1': range(0, 400), 'A2': range(400, 1000)}
        teststrings = ["Apple banana cherry date elderberry fig grape honeydew kiwi lemon mango."]
        complexity = get_book_complexity(
            teststrings, en_nlp, vocab_levels=VocabLevels(frequencies=frequencies, levels=levels),
            small_sample_size_cutoff=10 # 11 words >= 10, should calculate
        )
        # Calculation: {'A1': 10, 'A2': 1}. 95th percentile of 11 words is 10.45th word -> A2
        assert complexity["Vocab Level"] == 'A2'

    def test_complexities(self, en_nlp):
        files = glob("test/data/dummy_books/**/*.txt", recursive=True)
        complexities = list(get_complexities(files, nlp=en_nlp, vocab=None, known_morph_list=None, small_sample_size_cutoff=DEFAULT_SMALL_SAMPLE_SIZE_CUTOFF))
        assert len(list(complexities)) == 2
        assert complexities[0]["title"] == "dummy_book"
        assert complexities[0]["author"] == "dummy_books"
        assert complexities[0]["lang"] == "en"

    def test_grammar_depth_simple(self, ru_nlp):
        """Are grammar depth correct on a known short string?"""

        # let's not explode when we see non-Latin-1 text
        short_string = "Дедушка поцеловал Лидиньку"

        doc = next(ru_nlp.pipe([short_string]))
        assert ComplexityCalculators.sentence_grammar_depth(next(doc.sents)) == 2


import io
from book_complexity.book_complexity import frequencies_from_csv

class TestFrequenciesFromCSV:
    def test_basic_parsing(self):
        """Test basic CSV parsing for frequencies_from_csv."""
        csv_content = b"lemma,inflection\napple,apples\nbanana,bananas\ncherry,cherries"
        mock_file = io.BytesIO(csv_content)
        expected = {
            "apples": 0,  # Rank 0 for the first item after header
            "bananas": 1, # Rank 1 for the second
            "cherries": 2 # Rank 2 for the third
        }
        result = frequencies_from_csv(mock_file)
        assert result == expected

    def test_empty_csv_after_header(self):
        """Test parsing an empty CSV (only header)."""
        csv_content = b"lemma,inflection\n"
        mock_file = io.BytesIO(csv_content)
        expected = {}
        result = frequencies_from_csv(mock_file)
        assert result == expected

    def test_csv_with_only_header_no_newline(self):
        """Test parsing a CSV with only a header and no trailing newline."""
        csv_content = b"lemma,inflection"
        mock_file = io.BytesIO(csv_content)
        expected = {}
        result = frequencies_from_csv(mock_file)
        assert result == expected

    def test_unicode_characters(self):
        """Test parsing CSV with unicode characters."""
        csv_content = "lemma,inflection\nяблоко,яблоки\nбанан,бананы".encode('utf-8')
        mock_file = io.BytesIO(csv_content)
        expected = {
            "яблоки": 0,
            "бананы": 1
        }
        result = frequencies_from_csv(mock_file)
        assert result == expected

    def test_malformed_row_raises_value_error(self):
        """Test that a row with an incorrect number of columns raises a ValueError."""
        # This CSV has a header, one good row, one malformed row (1 col), one good row.
        csv_content = b"lemma,inflection\napple,apples\nbanana\ncherry,cherries"
        mock_file = io.BytesIO(csv_content)
        with pytest.raises(ValueError) as excinfo:
            frequencies_from_csv(mock_file)
        assert "Expected 2 columns" in str(excinfo.value)
        assert "Row content: ['banana']" in str(excinfo.value)
        assert "data line 2" in str(excinfo.value) # 'banana' is the 2nd data line (i=1)

    def test_empty_line_in_csv_raises_value_error(self):
        """Test that an empty line in the CSV (after header) raises a ValueError."""
        # This CSV has a header, then an empty line, then valid data.
        csv_content = b"lemma,inflection\n\napple,apples\nbanana,bananas\n"
        mock_file = io.BytesIO(csv_content)
        with pytest.raises(ValueError) as excinfo:
            frequencies_from_csv(mock_file)
        # The first data line (i=0) is the empty line.
        assert "Malformed row" in str(excinfo.value) 
        assert "data line 1" in str(excinfo.value) # Empty line is the 1st data line (i=0)
        assert "got 0" in str(excinfo.value) # len([]) is 0
