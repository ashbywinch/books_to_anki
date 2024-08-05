# Tools for learning languages from books

Reading books and short stories is a great tool for language learning, and many languages
have lots of public domain books available for free download.
However, it can be difficult to find books at an appropriate level, and frustrating to read a book
as a language learner if your state of flow is constantly interrupted by having to look up words.

This package contains

1. **book-to-flashcard**, a tool to turn a book into learning material. Currently it supports
flashcards suitable for importing into Anki (<https://apps.ankiweb.net/>), as well as full side-by-side translations (with the original text in the left column and translated text in the right column).

    Reading a book in small discrete chunks with easily accessible translations can massively improve "flow" for language learners.

2. **books-complexity**, a tool to calculate various complexity metrics on text files. If you have a large corpus of texts, this can be used to identify suitable foreign language texts to study.

## Warning

These tools lean heavily on AI. AI is pretty neat but it is often also very dumb. Its translations will not be nearly as good as human translations, and sometimes they will be outright wrong. But the're usually good enough to be helpful in the learning context. Make sure you always start with foreign language material and translate it into your native language - if you try it the other way round, you won't be able to tell when the AI is making silly mistakes.

## Installation

Install python from here <https://www.python.org/downloads/> if you don't already have it.
Download this repo.

From a command line, run

```powershell
> python -m pip install .
```

Use the instructions at the top of the page here <https://spacy.io/usage/> to configure and install the pipeline for the **language your books are written in**. Make a note of the name of the pipeline (something like "fi_core_news_sm" for Finnish, or "ru_core_news_sm" for Russian).

You will need a free DeepL account (<https://www.deepl.com/signup?cta=free-doctrans-signup>) which will give you an API key that allows you to translate a fixed amount of text per month. At the time of writing the monthly allowance is 500,000 characters, which is enough for quite a bit of literature.

## book-to-flashcard

This is a command line tool (and also a python package) that can take text files, and generate learning material.

### Generating Anki decks

Anki (<https://apps.ankiweb.net/>) is a flashcard application that uses spaced repetition to help with knowledge acquisition. Cards are bundled into "decks" containing sets of related learning material.

**book-to-flashcard** will generate one anki deck per text file. Each deck will contain the entire text of that file, in order, split into flash-card-sized chunks, with the original text on the front of the card and the translated text on the back of the card. All the decks will be bundled into a single Anki .apkg file.

**book-to-flashcard** uses AI language parsing (via the spacy library) to try and split long sentences in such a way that they can be individually understood and translated without context.

DeepL is used to translate each card to a language of the user's choice. The list of available languages can be found here: <https://developers.deepl.com/docs/resources/supported-languages#target-languages>

The length of the "text chunks" and the size of the font on the cards is configurable.

#### Examples

See <https://developers.deepl.com/docs/resources/supported-languages#target-languages> for the list of language codes that the translate option understands.

```Powershell
book-to-flashcard from-text 'my-russian-book.txt' pipeline 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' --lang 'EN-GB' to-anki --fontsize=20 'all_my_books.apkg'
```

```Powershell
book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' --lang 'EN-GB' to-anki 'all_my_books.apkg'
```

### Generating side-by-side translations

This allows you to generate HTML files (one for each of your source text files) with the original text in the left column and the translated text in the right column. As with the flash cards, the text is split using AI into chunks that are individually translated, so it's easy to understand how the translated text matches up to the source.

The size of the chunks is configurable, as well as the font size in the HTML output. For easy books you may like to use smaller chunks and larger fonts - for complex books and for more experienced language learners, larger chunks and smaller fonts may be easier to read.

```Powershell
book-to-flashcard from-text 'my-russian-book.txt' pipeline --maxfieldlen 70 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' --lang 'EN-GB' to-sidebyside --fontsize=20 
```

```Powershell
book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' --lang 'EN-GB' to-sidebyside
```

### Advanced usage

Reading and writing to an intermediate CSV format is also supported. For example, you can

* generate a CSV of cards without translations, in order to try multiple different translations without reprocessing the source files (processing the source files can take quite some time, if you have lots of text to process).

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' to-csv 'all_my_books.csv'
> book-to-flashcard from-csv 'all_my_books.csv' translate --deeplkey 'YOUR_KEY' lang='EN-GB' to-anki 'all_my_books_english.apkg'
> book-to-flashcard from-csv 'all_my_books.csv' translate --deeplkey 'YOUR_KEY' lang='ES' to-anki 'all_my_books_spanish.apkg'
```

* generate a CSV of translated cards, and then use that file to experiment with output in a variety of font sizes without re-translating the cards (which would use up your DeepL API key)

```Powershell
> book-to-flashcard from-folder './docs/books/' pipeline 'ru_core_news_sm' translate --deeplkey 'YOUR_KEY' lang='EN-GB' to-csv 'all_my_books.csv'
> book-to-flashcard from-csv 'all_my_books.csv' to-anki --fontsize 30 'all_my_books_big.apkg'
> book-to-flashcard from-csv 'all_my_books.csv' to-anki -fontsize 14 'all_my_books_small.apkg'
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

    Given the list of words that you know, what percentage of the words in this text are known to you.

* Vocabulary Level
    This is calculated if you supply a word frequency list for the language of the text. Frequency files for several languages can be found at <https://mortii.github.io/anki-morphs/user_guide/setup/prioritizing.html?highlight=frequency#custom-frequency-files>
    We divide the frequency list into subsets roughly corresponding to the CEFR levels:

    | Result | CEFR level |
    |--------|------------|
    | 0      | A1         |
    | 1      | A2         |
    | 2      | B1         |
    | 3      | B2         |
    | 4      | C1         |
    | 5      | C2         |

    Currently this option returns the maximum "level" of all the words in the text, although working from the 90% percentile would be a great improvement (watch this space!). So, a text with only very simple words would be assessed as level 0, and a text with many very unusual words would be assessed as level 5. It ignores words that are not in the frequency list. 

Use the help command to get more details on the options for these commands:

```Powershell
> book-complexity --help
> books-complexity --help
```
