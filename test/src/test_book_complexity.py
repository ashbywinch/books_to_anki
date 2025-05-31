"""Tests for book_complexity module"""

import pytest
from glob import glob
import io
from book_complexity import get_book_complexity, make_nlp
from book_complexity import ComplexityCalculators
from book_complexity.book_complexity import (
    VocabLevelCalculator,
    get_complexities,
    DEFAULT_SMALL_SAMPLE_SIZE_CUTOFF,
    frequencies_from_csv,
    get_book_props,
)
from book_complexity.vocabulary_levels import VocabLevels
from book_to_flashcards import trim_title
from spacy.tokens import Doc


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
        """Дедушка Ириней очень любил маленьких детей, то есть таких детей, которые умны, 
            слушают, когда им что говорят, не зевают по сторонам и не глядят в окошко, 
            когда маменька им показывает книжку""",
    ]
    # Use io.StringIO to make it an iterable of strings (TextIO)
    input_text_io = io.StringIO("\n".join(long_strings))
    yield get_book_complexity(input_text_io, ru_nlp)


class TestBookComplexityOnMultipleLongerStrings:

    def test_word_count_long(self, complexity):
        assert complexity["Word Count"] == 53

    def test_sentence_count_long(self, complexity):
        assert complexity["Sentence Count"] == 5

    def test_mean_grammar_depth_long(self, complexity):
        assert complexity["Mean Grammar Depth"] == 4.2

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


class TestTrimTitleSuffixBySeparator:
    @pytest.mark.parametrize(
        "title, separator, expected",
        [
            ("Part1_Part2_End", "_", "Part1_Part2"),
            ("Chapter1-SectionA-Paragraph5", "-", "Chapter1-SectionA"),
            ("Filename.version.tar.gz", ".", "Filename.version.tar"),
            ("NoSeparatorHere", "_", "NoSeparatorHere"), # Separator not in title
            ("EndsWithSeparator_", "_", "EndsWithSeparator"), # Title ends with separator
            ("_StartsWithSeparator", "_", ""), # Title starts with separator, first part is empty
            ("Multi_Char__Separator_End", "__", "Multi_Char"), # Multi-character separator
            ("SimpleTitle", None, "SimpleTitle"), # No separator provided
            ("", "_", ""), # Empty title
            ("word", "word", ""), # Separator is the whole string
            ("prefix_suffix", "prefix_", ""),
        ],
    )
    def test_trim_title_various_cases(self, title, separator, expected):
        assert trim_title(title, separator) == expected

    def test_trim_title_no_separator_arg(self):
        assert trim_title("ATitleWith_NoSeparatorArgProvided") == "ATitleWith_NoSeparatorArgProvided"

    def test_trim_title_empty_separator(self):
        # Python's split behaves this way with an empty string separator
        with pytest.raises(ValueError, match="empty separator"):
            trim_title("Title", "")


class TestGetBookProps:
    @pytest.mark.parametrize(
        "filepath, suffix_separator, expected_title, expected_author",
        [
            ("test/data/Author Name/Book Title.txt", None, "Book Title", "Author Name"),
            ("test/data/Another Author/A Great Novel_meta.epub", "_meta", "A Great Novel", "Another Author"),
            ("data/Tolstoy/War and Peace.part1.txt", ".part1", "War and Peace", "Tolstoy"),
            ("Some Author/JustTheBook.txt", None, "JustTheBook", "Some Author"),
            ("Deep/Nested/Path/Author/Book.txt", None, "Book", "Author"),
            ("Author/Book With Spaces.txt", None, "Book With Spaces", "Author"),
            ("Author/Book.multi.dots.txt", ".txt", "Book.multi.dots", "Author"), # .stem handles last suffix
            ("Author/Book.multi.dots.txt", ".dots", "Book.multi", "Author"),
        ]
    )
    def test_get_book_props_various_cases(self, filepath, suffix_separator, expected_title, expected_author, fs):
        # fs is the pyfakefs fixture, create dummy file
        fs.create_file(filepath)
        props = get_book_props(filepath, remove_title_suffix_after=suffix_separator)
        assert props["title"] == expected_title
        assert props["author"] == expected_author

    def test_get_book_props_no_suffix_separator_provided(self, fs):
        filepath = "test_author/test_book_raw.txt"
        fs.create_file(filepath)
        props = get_book_props(filepath)
        assert props["title"] == "test_book_raw"
        assert props["author"] == "test_author"

    def test_get_book_props_suffix_separator_not_found(self, fs):
        filepath = "test_author/test_book_actual.txt"
        fs.create_file(filepath)
        props = get_book_props(filepath, remove_title_suffix_after="_nonexistent")
        assert props["title"] == "test_book_actual"
        assert props["author"] == "test_author"


class TestMakeNlp:
    def test_make_nlp_valid_model(self, en_nlp):
        assert en_nlp is not None
        assert "lemmatizer" not in en_nlp.pipe_names
        assert "ner" not in en_nlp.pipe_names
        assert "attribute_ruler" not in en_nlp.pipe_names
        assert "parser" in en_nlp.pipe_names
        assert "tagger" in en_nlp.pipe_names


class TestVocabularyLevels:
    @pytest.fixture
    def sample_frequencies(self):
        return {"apple": 10, "banana": 100, "cherry": 1000, "date": 0, "elderberry": 500, "super_high_freq": 3000}

    @pytest.fixture
    def sample_levels_valid_contiguous(self):
        # Contiguous, non-overlapping, starts at 0
        return {"A1": range(0, 50), "A2": range(50, 500), "B1": range(500, 2000)}
    
    @pytest.fixture
    def sample_levels_valid_single(self):
        # Single level, must start at 0
        return {"OnlyLevel": range(0, 1000)}

    @pytest.fixture
    def vocab_levels_instance(self, sample_frequencies, sample_levels_valid_contiguous):
        return VocabLevels(sample_frequencies, sample_levels_valid_contiguous)

    @pytest.fixture
    def dummy_token_factory(self, en_nlp):
        vocab = en_nlp.vocab
        def _factory(text):
            return Doc(vocab, words=[text])[0]
        return _factory

    def test_init_success_contiguous_levels(self, sample_frequencies, sample_levels_valid_contiguous):
        vl = VocabLevels(sample_frequencies, sample_levels_valid_contiguous)
        assert vl.frequencies == sample_frequencies
        assert vl.levels == sample_levels_valid_contiguous
        assert vl.default_level == "A1"

    def test_init_success_single_level(self, sample_frequencies, sample_levels_valid_single):
        vl = VocabLevels(sample_frequencies, sample_levels_valid_single)
        assert vl.frequencies == sample_frequencies
        assert vl.levels == sample_levels_valid_single
        assert vl.default_level == "OnlyLevel"

    def test_init_empty_levels_raises_valueerror(self, sample_frequencies):
        with pytest.raises(ValueError, match="Vocabulary 'levels' dictionary cannot be empty"):
            VocabLevels(sample_frequencies, {})

    def test_init_levels_not_starting_at_zero_raises_valueerror(self, sample_frequencies):
        levels_not_at_zero = {"L1": range(10, 20), "L2": range(20, 30)}
        with pytest.raises(ValueError, match="Vocabulary level definitions must start at 0"):
            VocabLevels(sample_frequencies, levels_not_at_zero)
        
        single_level_not_at_zero = {"Only": range(10, 100)}
        with pytest.raises(ValueError, match="Vocabulary level definitions must start at 0"):
            VocabLevels(sample_frequencies, single_level_not_at_zero)

    def test_init_gappy_levels_raises_valueerror(self, sample_frequencies):
        # Starts at 0, but gappy
        gappy_levels = {"A1": range(0, 50), "B1": range(100, 200)} 
        with pytest.raises(ValueError, match="Vocabulary levels have a gap"):
            VocabLevels(sample_frequencies, gappy_levels)

    def test_init_overlapping_levels_raises_valueerror(self, sample_frequencies):
        # Starts at 0, but overlapping
        overlapping_levels = {"A1": range(0, 100), "A2": range(50, 150)} 
        with pytest.raises(ValueError, match="Vocabulary levels overlap"):
            VocabLevels(sample_frequencies, overlapping_levels)
    
    def test_init_misordered_but_overlapping_levels_raises_valueerror(self, sample_frequencies):
        # Starts at 0, but overlapping (order in dict doesn't matter for logic)
        misordered_overlapping = {"A2": range(50,150), "A1": range(0,100)}
        with pytest.raises(ValueError, match="Vocabulary levels overlap"):
            VocabLevels(sample_frequencies, misordered_overlapping)

    def test_init_misordered_gappy_levels_raises_valueerror(self, sample_frequencies):
        # Starts at 0, but gappy (order in dict doesn't matter for logic)
        misordered_gappy = {"B1": range(100, 200), "A1": range(0, 50)}
        with pytest.raises(ValueError, match="Vocabulary levels have a gap"):
            VocabLevels(sample_frequencies, misordered_gappy)

    @pytest.mark.parametrize(
        "token_text, expected_level",
        [
            ("apple", "A1"),      # Freq 10, in A1 (0-50)
            ("APPLE", "A1"),      # Case insensitivity, Freq 10
            ("banana", "A2"),     # Freq 100, in A2 (50-500)
            ("elderberry", "B1"), # Freq 500, in B1 (500-2000)
            ("cherry", "B1"),     # Freq 1000, in B1 (500-2000)
            ("date", "A1"),        # Freq 0, in A1 (0-50)
            ("unknown_word", "A1"),# Not in frequencies, freq defaults to 0, in A1
            ("fig", "A1"),         # Not in frequencies, treated as freq 0, default A1
            ("super_high_freq", "A1") # Freq 3000, above B1's range (500-2000), defaults to A1
        ],
    )
    def test_get_level_various_tokens(self, vocab_levels_instance, dummy_token_factory, token_text, expected_level):
        token = dummy_token_factory(token_text)
        assert vocab_levels_instance.get_level(token) == expected_level

    def test_get_level_frequency_between_valid_levels(self, sample_frequencies, sample_levels_valid_contiguous, dummy_token_factory):
        frequencies_with_mid_word = {**sample_frequencies, "midfruit": 499}
        # sample_levels_valid_contiguous = {"A1": range(0, 50), "A2": range(50, 500), "B1": range(500, 2000)}
        vl = VocabLevels(frequencies_with_mid_word, sample_levels_valid_contiguous)
        token_mid = dummy_token_factory("midfruit") # freq 499 -> A2
        assert vl.get_level(token_mid) == "A2"
        token_boundary = dummy_token_factory("elderberry") # freq 500 -> B1
        assert vl.get_level(token_boundary) == "B1"


class TestVocabLevelCalculator:
    @pytest.fixture
    def sample_vocab_levels_instance(self):
        # Re-using fixtures from TestVocabularyLevels or creating specific ones
        frequencies = {"apple": 10, "banana": 100, "cherry": 500, "date": 1000}
        levels = {"A1": range(0, 50), "A2": range(50, 500), "B1": range(500, 2000)}
        return VocabLevels(frequencies, levels)

    @pytest.fixture
    def dummy_token_factory_for_calc(self, en_nlp):
        vocab = en_nlp.vocab
        def _factory(text):
            return Doc(vocab, words=[text])[0]
        return _factory

    def test_percentile_calculation(self, sample_vocab_levels_instance):
        # sample_vocab_levels_instance is not directly used by percentile, it's a static method effectively
        # but VocabLevelCalculator needs it for its own init. Here we test percentile directly.
        calc = VocabLevelCalculator(sample_vocab_levels_instance, small_sample_size_cutoff=0)
        
        bar_chart1 = {"A1": 10, "A2": 80, "B1": 10} # Total 100
        # 95th percentile: 10 (A1) + 80 (A2) = 90. Next is B1.
        assert calc.percentile(bar_chart1, 95.0) == "B1" 
        # 5th percentile: falls into A1
        assert calc.percentile(bar_chart1, 5.0) == "A1"
        # 10th percentile: falls into A1
        assert calc.percentile(bar_chart1, 10.0) == "A1"
        # 10.1th percentile: falls into A2
        assert calc.percentile(bar_chart1, 10.1) == "A2"
        # 50th percentile: falls into A2
        assert calc.percentile(bar_chart1, 50.0) == "A2"
        # 90th percentile: falls into A2 (10 A1 + 80 A2 = 90)
        assert calc.percentile(bar_chart1, 90.0) == "A2"
        # Max percentile
        assert calc.percentile(bar_chart1, 100.0) == "B1"

        bar_chart2 = {"A1": 5, "A2": 5} # Total 10
        # 95th percentile: 5 (A1) + 5 (A2) = 10. Falls into A2.
        assert calc.percentile(bar_chart2, 95.0) == "A2"
        # 50th percentile: falls into A1
        assert calc.percentile(bar_chart2, 50.0) == "A1"
        # 50.1th percentile: falls into A2
        assert calc.percentile(bar_chart2, 50.1) == "A2"

        bar_chart_single = {"C1": 100}
        assert calc.percentile(bar_chart_single, 1.0) == "C1"
        assert calc.percentile(bar_chart_single, 95.0) == "C1"
        assert calc.percentile(bar_chart_single, 100.0) == "C1"

    def test_percentile_empty_chart_raises_error(self, sample_vocab_levels_instance):
        calc = VocabLevelCalculator(sample_vocab_levels_instance, 0)
        with pytest.raises(ValueError, match="empty bar_chart"):
            calc.percentile({}, 95.0)

    def test_percentile_zero_total_datapoints_raises_error(self, sample_vocab_levels_instance):
        calc = VocabLevelCalculator(sample_vocab_levels_instance, 0)
        with pytest.raises(ValueError, match="zero total datapoints"):
            calc.percentile({"A1":0, "A2":0}, 95.0)

    def test_process_token(self, sample_vocab_levels_instance, dummy_token_factory_for_calc):
        calc = VocabLevelCalculator(sample_vocab_levels_instance, small_sample_size_cutoff=0)
        token_apple = dummy_token_factory_for_calc("apple") # Freq 10 -> A1
        assert calc.process_token(token_apple) == {"A1": 1}
        token_banana = dummy_token_factory_for_calc("banana") # Freq 100 -> A2
        assert calc.process_token(token_banana) == {"A2": 1}
        token_unknown = dummy_token_factory_for_calc("zyxw") # Freq 0 -> A1 (default)
        assert calc.process_token(token_unknown) == {"A1": 1}

    def test_and_finally_below_cutoff(self, sample_vocab_levels_instance):
        calc = VocabLevelCalculator(sample_vocab_levels_instance, small_sample_size_cutoff=10)
        accumulated = {"A1": 5, "A2": 4} # Total 9, less than 10
        assert calc.and_finally(accumulated) == ""

    def test_and_finally_at_cutoff(self, sample_vocab_levels_instance):
        calc = VocabLevelCalculator(sample_vocab_levels_instance, small_sample_size_cutoff=10)
        accumulated = {"A1": 5, "A2": 5} # Total 10, at cutoff. 95th percentile is A2.
        assert calc.and_finally(accumulated) == "A2"

    def test_and_finally_above_cutoff(self, sample_vocab_levels_instance):
        calc = VocabLevelCalculator(sample_vocab_levels_instance, small_sample_size_cutoff=5)
        accumulated = {"A1": 8, "A2": 2} # Total 10. 95th percentile is A2 (8 A1 + 2 A2).
        assert calc.and_finally(accumulated) == "A2"

    def test_and_finally_empty_accumulation_returns_empty_string(self, sample_vocab_levels_instance):
        # This case should be caught by small_sample_size_cutoff if > 0
        # If cutoff is 0, then percentile will raise ValueError for empty dict
        calc_cutoff_0 = VocabLevelCalculator(sample_vocab_levels_instance, small_sample_size_cutoff=0)
        assert calc_cutoff_0.and_finally({}) == "" # due to try-except ValueError in and_finally
        
        calc_cutoff_5 = VocabLevelCalculator(sample_vocab_levels_instance, small_sample_size_cutoff=5)
        assert calc_cutoff_5.and_finally({}) == ""

    def test_combine_values(self, sample_vocab_levels_instance):
        calc = VocabLevelCalculator(sample_vocab_levels_instance, 0)
        dict1 = {"A1": 1, "A2": 2}
        dict2 = {"A2": 3, "B1": 4}
        expected = {"A1": 1, "A2": 5, "B1": 4}
        assert calc.combine_values(dict1, dict2) == expected
        assert calc.combine_values(dict1, {}) == dict1
        assert calc.combine_values({}, dict2) == dict2
        assert calc.combine_values({}, {}) == {}


