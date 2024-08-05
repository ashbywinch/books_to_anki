# Tools for learning languages from books

Reading books and short stories is a great tool for language learning, and many languages
have lots of public domain books available for free download.
However, it can be difficult to find books at an appropriate level, and frustrating to read a book
as a language learner if your state of flow is constantly interrupted by having to look up words.

This package contains

1. books-to-anki, a tool to turn a book into a set of flashcards suitable for importing into Anki (<https://apps.ankiweb.net/>). Reading a book via flashcards can massively improve "flow" for language learners.
2. books-complexity, a tool to calculate various complexity metrics on text files. If you have a large corpus of texts, this can be used to identify suitable foreign language texts to study.

## Installation

Install python from here <https://www.python.org/downloads/> if you don't already have it.
From a command line, run

```python
> python3 -m pip install book_language_tools 
```

Use the instructions at the top of the page here <https://spacy.io/usage/> to configure and install the pipeline for the **language your books are written in**. Make a note of the name of the pipeline (something like "fi_core_news_sm" for Finnish, or "ru_core_news_sm" for Russian).

## book-to-flashcard

This is a command line tool (and also a python package) that can take text files, and generate an anki package. The package will contain one anki deck per text file, and each deck will contain the entire text of that file in order, split into flash-card-sized chunks, with the original text on the front of the card and the translated text on the back of the card.  

book-to-flashcard uses AI language parsing (via the spacy library) to try and split long sentences in such a way that they can be individually understood and translated without context.

DeepL is used to translate each card to a language of the user's choice.

The length of the "text chunks" and the size of the font on the cards is configurable.

### Examples

```Powershell
book-to-flashcard from-text 'my-russian-book.txt' pipeline 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' --lang 'EN-GB' to-sidebyside --fontsize=20
```

```Powershell
book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' --lang 'EN-GB' to-anki 'all_my_books.apkg'
```

Reading and writing to an intermediate CSV format is also supported. For example, you can

* generate a CSV of cards without translations, in order to try multiple different translations without reprocessing the source files (processing the source files can take quite some time, if you have lots of text to process).

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' to-csv 'all_my_books.csv'
> book-to-flashcard from-csv 'all_my_books.csv' translate --deeplkey 'YOUR_KEY' lang='EN-GB' to-anki 'all_my_books.apkg'
> book-to-flashcard from-csv 'all_my_books.csv' translate --deeplkey 'YOUR_KEY' lang='EN-US' to-anki 'all_my_books.apkg'
```

* generate a CSV of translated cards, and then use that file to experiment with output in a variety of font sizes without re-translating the cards (which would use up your DeepL API key)

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' lang='EN-GB' to-csv 'all_my_books.csv'
> book-to-flashcard from-csv 'all_my_books.csv' to-anki --fontsize 30 'all_my_books.apkg'
> book-to-flashcard from-csv 'all_my_books.csv' to-anki -fontsize 14 'all_my_books.apkg'
```

There is also a dummy translation option that can be used to make experiments without using up a DeepL API key. This provides "translations" that are just the original text reversed, so "Hi!" becomes "!iH".

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' dummy-translate to-csv 'all_my_books.csv'
```

Alternatively, leaving out the translation option altogether gives output with blank translations.

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' to-csv 'all_my_books.csv'
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
* Vocabulary Level
    This is calculated if you supply a word frequency list for the language of the text. Frequency files for several languages can be found at <https://mortii.github.io/anki-morphs/user_guide/setup/prioritizing.html?highlight=frequency#custom-frequency-files>
    It divides the frequency list into subsets roughly corresponding to the CEFR levels:

    0. A1
    1. A2
    2. B1
    3. B2
    4. C1
    5. C2

    Currently it returns the maximum "level" of all the words in the text, although working from the 90% percentile would be a great improvement (watch this space!). It ignores words that are not in the frequency list.

```Powershell
book-complexity --help
books-complexity --help
```
