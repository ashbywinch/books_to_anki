# Tools for learning languages from books

Reading books and short stories is a great tool for language learning, and many languages have lots of public domain books available for free download.
However, it can be difficult to find books at an appropriate level, and frustrating to read a book as a language learner if your state of flow is constantly interrupted by having to look up words. Reading a book in small discrete chunks with easily accessible translations can massively improve "flow" for language learners.

This package contains

1.  **`book-to-flashcard`**:
    *   Converts text files into Anki flashcard decks (.apkg files)
    *   Splits text into manageable chunks that make sense standalone
    *   Translates chunks to your language of choice.
    *   Allows intermediate JSONL format for staged processing (e.g., split up text first and translate separately, or use the flash card data for other processing outside this tool).
    *   Includes a dummy translation option for trying out the tool without translation API usage.

2.  **`books-complexity` / `book-complexity`**:
    *   Calculates various complexity metrics for text files.
    *   Metrics include: word count, sentence count, words per sentence, mean word length, mean grammar depth (based on parse trees).
    *   Can estimate "words known" and "percent words known" if a list of known words is provided (e.g., from AnkiMorphs).
    *   Provides a "Vocabulary Level" based on word frequency lists, very vaguely corresponding to CEFR levels.

## Warning

`book-to-flashcard` uses AI for translations. AI is pretty good but it is often also very dumb. Its translations will not be as good as human translations, and sometimes they will be wrong. But the're usually good enough to be helpful in the learning context. If you start with foreign language material and translate it into your native language (rather than the other way round), you'll be able to tell when the AI is making silly mistakes.

## Installation

Install python from here <https://www.python.org/downloads/> if you don't already have it.
Download this repo.

From a command line, run

```powershell
> python -m pip install .
```

Use the instructions at the top of the page here <https://spacy.io/usage/> to configure and install the pipeline for the **language your books are written in**. Make a note of the name of the pipeline (something like "fi_core_news_sm" for Finnish, or "ru_core_news_sm" for Russian).

You will need the [opencode](https://opencode.ai) CLI installed and logged in with an OpenCode Go account (run `opencode` once and follow the login flow). Translations are made with deepseek models served by the OpenCode Go API, and the API key is picked up automatically from opencode's auth file, or from the `OPENCODE_API_KEY` environment variable if you prefer.

## book-to-flashcard

This is a command line tool (and also a python package) that can take text files, and generate learning material.

### Generating Anki decks

Anki (<https://apps.ankiweb.net/>) is a flashcard application that uses spaced repetition to help with knowledge acquisition. Cards are bundled into "decks" containing sets of related learning material.

**book-to-flashcard** will generate one anki deck per text file. Each deck will contain the entire text of that file, in order, split into flash-card-sized chunks, with the original text on the front of the card and the translated text on the back of the card. All the decks will be bundled into a single Anki .apkg file.

**book-to-flashcard** uses AI language parsing to try and split long sentences in such a way that they can be individually understood and translated without context.

Translations are made with deepseek models through the OpenCode Go API (the `opencode-go` provider). Cards are translated in batches, and each batch is translated in the context of the text that immediately precedes it in the book, so pronouns, references and register stay consistent across cards without a round trip per card.

The length of the "text chunks" and the size of the font on the cards is configurable.

#### Examples

```Powershell
book-to-flashcard from-text 'my-russian-book.txt' pipeline 'ru_core_news_sm' translate --lang 'English' to-anki --fontsize=20 'all_my_books.apkg'
```

```Powershell
book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' translate --lang 'English' to-anki 'all_my_books.apkg'
```

The `--lang` option is a free-text description of the language to translate into (e.g. `English`, `Spanish`, `French`). Use `--model` to pick a different model (the default is `deepseek-v4-flash`; `deepseek-v4-pro` is also available).

### Advanced usage

Reading and writing to an intermediate jsonl format is also supported. For example, you can

* generate a file of cards without translations, in order to try multiple different translations without reprocessing the source files (processing the source files can take quite some time, if you have lots of text to process).

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' to-jsonl 'all_my_books.jsonl'
> book-to-flashcard from-jsonl 'all_my_books.jsonl' translate --lang 'English' to-anki 'all_my_books_english.apkg'
> book-to-flashcard from-jsonl 'all_my_books.jsonl' translate --lang 'Spanish' to-anki 'all_my_books_spanish.apkg'
```

* generate a file of translated cards, and then use that file to experiment with output in a variety of font sizes without re-translating the cards (which would use up your translation quota)

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' translate --lang 'English' to-jsonl 'all_my_books.jsonl'
> book-to-flashcard from-jsonl 'all_my_books.jsonl' to-anki --fontsize 30 'all_my_books_big.apkg'
> book-to-flashcard from-jsonl 'all_my_books.jsonl' to-anki -fontsize 14 'all_my_books_small.apkg'
```

There is also a dummy translation option that can be used to make experiments without using up translation quota. This provides "translations" that are just the original text reversed, so "Hi!" becomes "!iH".

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' dummy-translate to-jsonl 'all_my_books.jsonl'
```

Alternatively, leaving out the translation option altogether gives output with blank translations.

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' to-jsonl 'all_my_books.jsonl'
```

## books-complexity and book-complexity

These are command line tools (and also a python package "book_complexity") to calculate various complexity metrics for texts.

The metrics included are

* Word count
* Sentence count
* Words per sentence
* Mean word length
* Mean grammar depth

    This is calculated by making a grammatical tree from each sentence, and calculating the depth of that tree. So for example, a sentence using a lot of nested parentheses might have a very large depth, whereas the sentence "Jane eats apples" has a depth of 2.

* Words known

    This can be calculated if you provide a list of all the words you already know. If you've been using Anki for language learning, the extension "AnkiMorphs" can provide you with a list of words that are considered mature by Anki.

* Percent words known

    Given the list of words that you know, what percentage of the words in this text are known to you.

* Vocabulary Level
    This is calculated if you supply a word frequency list for the language of the text. Frequency files for several languages can be found at <https://mortii.github.io/anki-morphs/user_guide/setup/prioritizing.html?highlight=frequency#custom-frequency-files>
    We divide the frequency list into subsets that extremely vaguely correspond to the CEFR levels, using frequency ranges that are currently hardcoded

    | Range       | CEFR level |
    |-------------|------------|
    | 0-1000      | A1         |
    | 1000-2000   | A2         |
    | 2000-5000   | B1         |
    | 5000-10000  | B2         |
    | 10000-20000 | C1         |
    | >20000      | C2         |

    Currently this option returns the 95th percentile estimated "level" of all the words in the text. So, a text with only very simple words would be assessed as level A1, and a text with more than 5% of "B2" words would be assessed as level B2. It ignores words that are not in the frequency list.
    Texts with less than 250 words are not analysed since they can give misleading levels.

Use the help command to get more details on the options for these commands:

```Powershell
> book-complexity --help
> books-complexity --help
```
